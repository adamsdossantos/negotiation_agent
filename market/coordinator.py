"""
coordinate the simulation transactions
manages listing, browsing, negotiating
"""
from typing import List, Dict
from models.data_models import AgentArchetype, AgentState
from market.marketplace import Marketplace
from agents.base_agent import BaseAgent
from agents.inventory_utils import initialize_agent_inventory
from negotiation.negotiation_engine import NegotiationEngine
from config.settings import settings
import random
from utils.csv_logger import CSVLogger
from datetime import datetime
import uuid


class MarketCoordinator:
    """
    coordinate the simulation transactions
    """
    def __init__(self, num_agents:int = None):
        """
        initialize market coordinator
        """
        self.num_agents = num_agents or settings.num_agents
        self.marketplace = Marketplace()
        self.agents: Dict[str, BaseAgent] = {}
        self.negotiation_engine = None
        self.cycle_count = 0

        self.simulation_id = f"sim_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # initialize logger
        self.csv_logger = CSVLogger()
        print(f"Simulation ID: {self.simulation_id}")
        
        print("Market coordinator initialized")
        
    
    def initialize_agents(self):
        """
        initialize agents with inventory
        """
        print(f"\n{'='*60}")
        print(f"Initializing {self.num_agents} agents")
        print(f"{'='*60}")

        # get archetypes
        archetypes = settings.agent_archetypes[:self.num_agents]
        if len(archetypes) < self.num_agents:
            while len(archetypes) < self.num_agents:
                archetypes.extend(settings.agent_archetypes)
            archetypes = archetypes[:self.num_agents]

        # create agents
        for i, archetype_str in enumerate(archetypes):
            archetype = AgentArchetype(archetype_str)

            state = AgentState(
                agent_id=f"agent_{i:03d}",
                name=f"{archetype_str}_{i}",
                archetype=archetype,
                capital=settings.initial_capital_per_agent
            )

            agent = BaseAgent(state)
            initialize_agent_inventory(agent)
            self.agents[agent.state.agent_id] = agent

        print(f"{len(self.agents)} agents initialized")
        
        # initialize negotiation engine
        self.negotiation_engine = NegotiationEngine(self.marketplace, self.agents)
    

    def run_listing_phase(self):
        """
        phase 1: run the listing phase of the simulation
        """
        print(f"\n{'='*60}")
        print(f"PHASE 1: LISTING (Cycle {self.cycle_count})")
        print(f"{'='*60}")
        
        listings_created = 0

        for agent_id, agent in self.agents.items():
            # each agent list 1-2 items
            items_to_list = min(2, len(agent.state.inventory))

            if items_to_list == 0:
                print(f" {agent.state.name} has no items to list")
                continue

            # randon select items
            items = random.sample(agent.state.inventory, items_to_list)

            for item in items:
                existing = [
                    l for l in self.marketplace.get_all_listings()
                    if l.product.name == item.product.name and l.seller_id == agent_id
                ]

                if existing:
                    continue
            
                # mkt data
                market_avg = self.marketplace.get_average_price(item.product.category)

                # agent decides price
                decision = agent.decide_pricing(item, market_avg_price=market_avg)

                # post listing
                listing = self.marketplace.post_listing(
                    seller_id=agent_id,
                    product=item.product,
                    listing_price=decision.listing_price,
                    minimum_acceptable=decision.minimum_acceptable,
                    reasoning=decision.reasoning
                )

                listings_created += 1

                # log listing to CSV
                self.csv_logger.log_listing(
                    simulation_id=self.simulation_id,
                    cycle=self.cycle_count,
                    listing_data={
                        "listing_id": listing.listing_id,
                        "seller_id": listing.seller_id,
                        "product_name": listing.product.name,
                        "category": listing.product.category,
                        "listing_price": listing.listing_price,
                        "minimum_acceptable": listing.minimum_acceptable,
                        "status": "active",
                        "reasoning_summary": listing.reasoning[:200]
                    }
                )

        print(f" PHASE 1 COMPLETED: {listings_created} listings created")
        print(f" TOTAL ACTIVE LISTING: {len(self.marketplace.get_all_listings())}")
    

    def run_browsing_phase(self) -> List[Dict]:
        """
        phase 2: run the browsing phase of the simulation
        """
        print(f"\n{'='*60}")
        print("PHASE 2: BROWSING")
        print(f"{'='*60}")

        opportunities = []

        snapshot = self.marketplace.get_market_snapshot()

        agent_items = list(self.agents.items())
        random.shuffle(agent_items)


        for agent_id, agent in self.agents.items():
            # skip if agent does not have capital
            if agent.state.capital < 200:
                print(f" {agent.state.name} does not have enough capital {agent.state.capital:.2f}")
                continue

            # skip if inventory is full
            if len(agent.state.inventory) >= 5:
                print(f" {agent.state.name} inventory is full {len(agent.state.inventory)} items")
                continue


            # get listing excluiding own
            available_listings = self.marketplace.get_listings_excluding_seller(agent_id)

            if not available_listings:
                continue

            decision = agent.evaluate_listings(available_listings, snapshot)

           
            if decision:
                opportunities.append({
                    "buyer_id": agent.state.agent_id,
                    "buyer_name": agent.state.name,
                    "listing": decision['listing'],
                    "offered_price": decision['offer_price'],
                    "reasoning": decision['reasoning']
                })

                print(f"\n   🔍 DEBUG {agent.state.name}:")
                print(f"      Listing: {decision['listing']}")
                print(f"      Offer: {decision['offer_price']}")  # ← Fixed key
                print(f"      Reasoning: {decision['reasoning'][:80]}...")
            
       
    
        print(f" PHASE 2 COMPLETED: {len(opportunities)} opportunities identified")

        return opportunities

    
    def run_negotiation_phase(self, opportunities: List[Dict]):
        """
        phase 3: run the negotiation phase of the simulation
        """
        print(f"\n{'='*60}")
        print("PHASE 3: NEGOTIATIONS")
        print(f"{'='*60}")

        if not opportunities:
            print("\n No negotiation to run")
            return
        
        successful = 0
        failed = 0

        # shuffle to randomize 
        random.shuffle(opportunities)

        for opportunity in opportunities:
            # check if listing is available
            listing = self.marketplace.get_listing(opportunity['listing'].listing_id)
            if not listing:
                print(f" Listing no longer available: {opportunity['listing'].product.name}")
                continue

            # check if buyer still has capital
            buyer = self.agents[opportunity['buyer_id']]
            if buyer.state.capital < opportunity['offered_price']:
                print(f" {buyer.state.name} does not have enough capital")
                continue

            # run negotiation
            result = self.negotiation_engine.start_negotiation(
                buyer_id=opportunity['buyer_id'],
                listing=listing,
                initial_offer=opportunity['offered_price']
            )

            if result.get('success', False):
                successful += 1
                outcome = 'success'
                action = "ACCEPT"
                final_offer = result.get('final_price', opportunity['offered_price'])
            else:
                failed += 1
                outcome = 'failed'
                action = result.get("reason", "REJECT")
                final_offer = result.get('final_price', opportunity['offered_price'])
            
            # log negotiation
            buyer = self.agents[opportunity['buyer_id']]
            seller = self.agents[listing.seller_id]

            self.csv_logger.log_negotiation(
                simulation_id=self.simulation_id,
                cycle=self.cycle_count,
                negotiation_data={
                    "negotiation_id": result.get('negotiation_id'),
                    "buyer_id": opportunity['buyer_id'],
                    "seller_id": listing.seller_id,
                    "product_name": listing.product.name,
                    "listing_price": listing.listing_id,
                    "initial_offer": opportunity['offered_price'],
                    "final_offer": final_offer,
                    "outcome": outcome,
                    "rounds": result.get('rounds', 0),
                    "action": action
                }
            )

            # log transaction if successful
            if result.get('success', False):
                transactions = result.get('transactions')
                if transactions:
                    self.csv_logger.log_transactions(
                        simulation_id=self.simulation_id,
                        cycle=self.cycle_count,
                        transaction_data={
                            "transaction_id": transactions[0].transaction_id,
                            "buyer_id": transactions.buyer_id,
                            "buyer_archetype": buyer.state.archetype.value,
                            "seller_id": transactions.seller_id,
                            "seller_archetype": seller.state.archetype.value,
                            "product_name": transactions.product.name,
                            "category": transactions.product.category,
                            "listing_price": listing.listing_price,
                            "final_price": transactions.final_price,
                            "profit": transactions.profit(),
                            "margin": transactions.margin(),
                            "negotiation_rounds": result.get('rounds', 0)
                        }
                    )


            
        print(f"PHASE 3 COMPLETED: {successful} successful, {failed} failed")
    

    def run_cycles(self):
        """
        run one complete market cycle
        """
        self.cycle_count += 1

        print(f"\n{'='*60}")
        print(f" MARKET CYCLE {self.cycle_count}")
        print(f"{'='*60}")

        # phase 1 listing
        self.run_listing_phase()

        # phase 2 browsing
        opportunities = self.run_browsing_phase()

        # phase 3 negotiating
        self.run_negotiation_phase(opportunities)

        # log agent state at the end of cycle
        for agent_id, agent in self.agents.items():
            self.csv_logger.log_agent_state(
                simulation_id=self.simulation_id,
                cycle=self.cycle_count,
                agent_data={
                    "agent_id": agent.state.agent_id,
                    "name": agent.state.name,
                    "archetype": agent.state.archetype.value,
                    "capital": agent.state.capital,
                    "inventory_count": len(agent.state.inventory),
                    "inventory_value": agent.state.inventory_value,
                    "total_sales": agent.state.total_sales,
                    "total_purchases": agent.state.total_purchases,
                    "total_profit": agent.state.total_profit,
                    "total_assets": agent.state.total_assets,
                }
            )
        
        # log market metrics at the end the cycle
        stats = self.marketplace.get_statistics()

        # calculate total profit and avg margins
        total_profit = sum(agent.state.total_profit for agent in self.agents.values())

        # calculate avg margin from recent transactions
        recent_transactions = self.marketplace.completed_transactions[-20:]

        avg_margin = (
            sum(txn.margin for txn in recent_transactions) / len(recent_transactions)
            if recent_transactions else 0   
            )

        self.csv_logger.log_market_metrics(
            simulation_id=self.simulation_id,
            cycle=self.cycle_count,
            metrics_data={
                "active_listings": len(self.marketplace.get_all_listings()),
                "total_transactions": stats['total_transactions'],
                "total_volume": stats['total_volume'],
                "avg_transaction_price": stats['average_transaction'],
                "categories_listed":stats['categories_listed'],
                "total_profit": total_profit,
                "avg_margin": avg_margin,
            }
        )

        print(f"\n{'='*60}")
        print(f" MARKET CYCLE {self.cycle_count} COMPLETE")
        print(f"{'='*60}")


    def run_simulation(self, num_cycles:int=3):
        """
        run the entire simulation
        """
        print(f"\n{'='*60}")
        print(" STARTING MARKET SIMULATION")
        print(f" {num_cycles} cycles {self.num_agents} agents)")
        print(f"{'='*60}")

        # initialize agents
        if not self.agents:
            self.initialize_agents()
        
        # run cycles    
        for cycle in range(num_cycles):
            self.run_cycles()

        print(f"\n{'='*60}")
        print(" SIMULATION COMPLETED")
        print(f"{'='*60}")

    
    def get_agents_summary(self) -> List[Dict]:
        """
        get summary of all agents
        """
        summaries = []

        for agent_id, agent in self.agents.items():
            summaries.append({
                "id": agent.state.agent_id,
                "name": agent.state.name,
                "archetype": agent.state.archetype.value,
                "capital": agent.state.capital,
                "inventory_count": len(agent.state.inventory),
                "total_sales": agent.state.total_sales,
                "total_purchases": agent.state.total_purchases,
                "total_profit":agent.state.total_profit
            })
        
        return summaries
    










