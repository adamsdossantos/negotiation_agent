"""
negotiation enginee using LangGraph
manages multi-round negotiation between buyers and sellers
"""
from langgraph.graph import StateGraph, START, END
from typing import Dict, Optional
import uuid
import traceback

from negotiation.negotiation_nodes import(
    NegotiationState,
    buyer_makes_initial_offer, 
    seller_evaluates_offer, 
    buyer_evaluates_counter, 
    check_max_rounds, 
    finalized_success, 
    finalized_failure
    )

from models.data_models import Listing, Transaction, InventoryItem
from agents.base_agent import BaseAgent
from datetime import datetime

class NegotiationEngine:
    """
    manages the negotiation process
    """
    def __init__(self, marketplace, agents: Dict[str, BaseAgent]):
        """
        initialize negotiation engine
        Args:
            marketplace: Marketplace object
            agents: dictionary of agent_id BaseAgent
        """
        self.marketplace = marketplace
        self.agents = agents
        self.graph = self.build_graph()

        print("Initializing negotiation engine")


    def build_graph(self)-> StateGraph:
        """
        build the negotiation graph
        returns: StateGraph object
        """
        workflow = StateGraph(NegotiationState)
        
        # add nodes
        workflow.add_node("buyer_offer", lambda state: buyer_makes_initial_offer(state, self.agents))
        workflow.add_node("seller_evaluates", lambda state: seller_evaluates_offer(state, self.agents))
        workflow.add_node("buyer_evaluates", lambda state: buyer_evaluates_counter(state, self.agents))
        workflow.add_node("check_rounds", check_max_rounds)
        workflow.add_node("success", finalized_success)
        workflow.add_node("failure", finalized_failure)
    

        # set entry point
        #workflow.set_conditional_entry_point("buyer_offer")
        
        workflow.add_edge(START, "buyer_offer")

        # add edges
        workflow.add_edge("buyer_offer", "seller_evaluates")

        # conditional edges from seller evaluates
        workflow.add_conditional_edges(
            "seller_evaluates",
            self._route_seller_decision,
            {
                "success": "success",
                "failure": "failure",
                "continue": "buyer_evaluates"
            }
            )
        

        # conditional edges from buyers evaluates
        workflow.add_conditional_edges(
            "buyer_evaluates",
            self._route_buyer_decision,
            {
                "success": "success",
                "failure": "failure",
                "continue": "check_rounds"
            }
            )
        
        # conditional edges from round checks
        workflow.add_conditional_edges(
            "check_rounds",
            self._route_after_round_check,
            {
                "success": "success",
                "failure": "failure",
                "continue": "seller_evaluates"
            }
            )
        
        # terminal nodes
        workflow.add_edge("success", END)
        workflow.add_edge("failure", END)

        print(workflow.edges)

        return workflow.compile()


    
    def _wrap_nodes(self, node_func):
        """
        wrap node function
        """
        def wrapper(state):
            return node_func(state, self.agents)
        return wrapper

        
    def _route_seller_decision(self, state: NegotiationState):
        """
        determines the next step based on the seller's last action
        """
        if state['last_action'] == 'ACCEPT':
            return "success"
        elif state['last_action'] == 'REJECT':
            return "failure"
        else:        
            return "continue"
    
    def _route_buyer_decision(self, state: NegotiationState):
        """
        route based on buyer's decision
        """
        if state['last_action'] == 'ACCEPT':
            return "success"
        elif state['last_action'] == 'WALK_AWAY':
            return "failure"
        else:
            return "continue"
    
    def _route_after_round_check(self, state: NegotiationState):
        """
        route based on round check
        """
        if state['status'] == 'accepted':
            return "success"
        elif state['status'] in ['rejected', 'walked_away']:
            return "failure"
        else:
            return "continue"


    def start_negotiation(
            self, 
            buyer_id: str,  
            listing: Listing,
            initial_offer: float,
            max_rounds: int = 5
    )-> Dict:
        """
        start a new negotiation
        Args:
            buyer_id: buyer agent_id
            listing: items listed to be negotiated
            initial_offer:  buyer's initial offer

        Returns:
            dictionary with negotiation results
        """
        negotiation_id = f"neg_{uuid.uuid4().hex[:8]}"
        
        print(f"\n{'='*60}")
        print(f" STARTING NEGOTIATION ID: {negotiation_id}")
        print(f"{'='*60}")
        print(f" Product: {listing.product.name}")
        print(f" Seller: {listing.seller_id}")
        print(f" Buyer: {buyer_id}")
        print(f" Asking price: {listing.listing_price:.2f}")
        print(f" Initial Offer: {initial_offer:.2f}")
        
        # create initial state
        initial_state: NegotiationState = {
            "negotiation_id": negotiation_id,
            "buyer_id": buyer_id,
            "seller_id": listing.seller_id,
            "listing":listing,
            "initial_offer": initial_offer,
            "current_offer": initial_offer,
            "current_round": 1,
            "history": [],
            "status": 'active',
            "final_price": None,
            "last_action": None, 
            "last_message": ""
        }

        # run the graph
        try:
            final_state = self.graph.invoke(initial_state)

            # process result
            success = final_state['status'] == 'accepted'

            if success:
                # create transaction
                transaction = self._create_transaction(final_state)

                # remove listing from marketplace
                self.marketplace.remove_listing(listing.listing_id)

                # record transaction
                self.marketplace.record_transaction(transaction)

                # update agent state
                self._complete_transaction(transaction, final_state)

                return {
                    "success": True,
                    "transaction": transaction,
                    "final_price": final_state['final_price'],
                    "rounds": final_state['current_round'],
                    "history": final_state['history'],
                }
            else:
                # record failed negotiation in agent memory
                buyer = self.agents[buyer_id]
                seller = self.agents[listing.seller_id]

                buyer.add_negotiation_failure(
                    listing.seller_id,
                    f" Could not agree price for {listing.product.name}"
                    )
                
                seller.add_negotiation_failure(
                    buyer_id,
                    f" Could not agree price for {listing.product.name}"
                    )
                
                return {
                    "success": False,
                    "reason": final_state['status'],
                    "rounds": final_state['current_round'],
                    "history": final_state['history']
                }
        except Exception as e:
            print(f" Negotiation error {e}")
            traceback.print_exc()
            return {
                "success": False,
                "reason": f" Error: {str(e)}",
                "rounds": 0,
                "history": []
            }
            
              
    def _create_transaction(
            self, 
            state: NegotiationState, 
    ) -> Transaction:
        """
        create transaction  from successful negotiation
        """
        listing = state['listing']

        # find the inventory item to get cost basis
        seller = self.agents[state['seller_id']]
        cost_basis = listing.listing_price * 0.75

        for item in seller.state.inventory:
            if item.product.name == listing.product.name:
                cost_basis = item.cost_basis
                break
        
        transaction = Transaction(
            transaction_id=f"trx_{uuid.uuid4().hex[:8]}",
            buyer_id=state['buyer_id'],
            seller_id=state['seller_id'],
            product=listing.product,
            cost_basis=cost_basis,
            negotiation_rounds=state['current_round'],
            final_price=state['final_price']
        )

        return transaction
        

    def _complete_transaction(
            self, 
            transaction: Transaction, 
            state: NegotiationState
    ) -> Transaction:
        """
        update agent state after successful transaction
        """
        buyer = self.agents[transaction.buyer_id]
        seller = self.agents[transaction.seller_id]

        # find and remove item from seller inventory
        item_to_remove = None
        for item in seller.state.inventory:
            if item.product.name == transaction.product.name:
                item_to_remove = item
                break
        
        if item_to_remove:
            seller.state.inventory.remove(item_to_remove)

            # add to buyers inventory
            buyer.state.inventory.append(
                InventoryItem(
                    product=transaction.product,
                    cost_basis=transaction.cost_basis
                )
            )

        # update capital
        buyer.state.capital += transaction.cost_basis
        seller.state.capital -= transaction.cost_basis

        # update memory
        buyer.add_transaction_memory(transaction)
        seller.add_transaction_memory(transaction)

        # update memory summary
        buyer.update_memory_summary()
        seller.update_memory_summary()

        # learn patters from each other
        if transaction.margin > 20:
            buyer.learn_pattern(seller.state.agent_id,"Skilled negotiatior, got good margin")
        elif transaction.margin < 10:
            seller.learn_pattern(buyer.state.agent_id,"Tough negotiator, drives hard bargain")
        
        print("\n Transaction Completed:")
        print(f"  Buyer's capital: ${buyer.state.capital:.2f}")
        print(f"  Seller's capital: ${seller.state.capital:.2f}")
        print(f"  Seller's profit: ${transaction.profit:.2f} {transaction.margin:.2f}")
        
