"""
negociation function nodes for the state machine
each function represents a state in the negotiation process
"""
from typing import TypedDict, List, Optional, Literal
from models.data_models import NegotiationAction, NegotiationMessage, Listing
from agents.base_agent import BaseAgent

class NegotiationState(TypedDict):
    negotiation_id: str
    listing: Listing
    buyer_id: str
    seller_id: str
    listing: Listing
    initial_offer: float
    current_offer: float
    current_round: int
    history: List[NegotiationMessage]
    status: Literal["active", "accepted", "rejected", "walked_away"]
    final_price: Optional[float]
    last_action: Optional[str]
    last_message: str

def buyer_makes_initial_offer(state: NegotiationState, agents: dict) -> NegotiationState:
    """
    node: buyer makes initial offer
    Args:
        state: current negotiation state
        agents: dictionary of agent_id BaseAgent
    Returns:
        updated negotiation state
    """
    print(f"\n{'='*60}")
    print(f" ROUND {state['current_round']}: BUYER MAKES OFFER")
    print(f"{'='*60}")

    # creates message for initial offer
    message = NegotiationMessage(
        round_number=state['current_round'],
        from_agent=state['buyer_id'],
        to_agent=state['seller_id'],
        action=NegotiationAction.MAKE_OFFER,   
        price=state['initial_offer'],
        message=f"I'd like to offer ${state['initial_offer']:.2f} for {state['listing'].product.name}"
    )

    # update state
    state['history'].append(message)
    state['current_offer'] = state['initial_offer']
    state['last_action'] = 'MAKE_OFFER'
    state['last_message'] = message.message

    return state


def seller_evaluates_offer(state: NegotiationState, agents: dict)-> NegotiationState:
    """
    node: seller evalutates the offer
    Args:
        state: current negotiation state
        agents: dictionary of agent_id BaseAgent
    Returns:
        updated negotiation state
    """
    print(f"\n{'='*60}")
    print(f" ROUND {state['current_round']}: SELLER EVALUATES")
    print(f"{'='*60}")

    seller = agents[state['seller_id']]
    listing = state['listing']
    
    # get negotiation history
    history_strings = [
        f"Round {msg.round_number} - {msg.from_agent} - {msg.action.value}"
        f"{'$' + str(msg.price) if msg.price else ''} - {msg.message}"
        for msg in state['history']
    ]

    # get item for seller inventory
    inventory_item = None
    for item  in seller.state.inventory:
        if item.product.name == listing.product.name:
            inventory_item = item
            break
    
    if not inventory_item:
        print(f"ERROR: seller does not have {listing.product.name} in inventory")
        state['status'] = 'rejected'
        state['last_action'] = 'REJECT'
        return state

    # seller evalutates
    decision = seller.evaluate_offer_as_seller(
        offer_price = state['current_offer'],
        cost_basis = inventory_item.cost_basis,
        listing_price = listing.listing_price,
        minimum_acceptable = listing.minimum_acceptable,
        buyer_id = state['buyer_id'],
        round_num = state['current_round'],
        negotiation_history = history_strings
    )

    # create message based on decision
    if decision.action == NegotiationAction.ACCEPT:
        message_text = decision.message or f"I accepted your offer of {state['current_offer']:.2f}. Deal"
        state['status'] = 'accepted'
        state['final_price'] = state['current_offer']
    
    elif decision.action == NegotiationAction.REJECT:
        message_text = decision.message or f"Sorry, I cannot accept your offer of {state['current_offer']:.2f}. Deal"
        state['status'] = 'rejected'
    
    else:
        message_text = decision.message or f"I can do ${decision.price:.2f}"
        if decision.price is not None:
            state['current_offer'] = decision.price
    
    # record message
    message = NegotiationMessage(
        round_number=state['current_round'],
        from_agent=state['seller_id'],
        to_agent=state['buyer_id'],
        action=decision.action,
        price=decision.price,
        message=message_text
    )
    state['history'].append(message)
    state['last_action'] = decision.action.value
    state['last_message'] = message_text

    print(f" Seller: {message_text}")

    return state

def buyer_evaluates_counter(state: NegotiationState, agents: dict)-> NegotiationState:
    """
    node: buyer evaluates counter offer
    Args:
        state: current state
        agents: dictionary of agent_id BaseAgent
    Returns:
        updated state
    """
    # increment round for buyer response
    state['current_round'] += 1

    print(f"\n{'='*60}")
    print(f" ROUND {state['current_round']}: BUYER EVALUATES")
    print(f"{'='*60}")

    buyer = agents[state['buyer_id']]

    history_strings = [
         f"Round {msg.round_number} - {msg.from_agent} - {msg.action.value}"
        f"{'$' + str(msg.price) if msg.price else ''} - {msg.message}"
        for msg in state['history']
        ]
    
    # get buyer last offer
    buyer_last_offer = state['initial_offer']
    for msg in reversed(state['history']):
        if msg.from_agent == state['buyer_id'] and msg.price:
            buyer_last_offer = msg.price
            break
    
    # buyer evaluates
    decision = buyer.evaluate_counter_as_buyer(
        counter_price=state['current_offer'],
        my_last_offer=buyer_last_offer,
        listing=state['listing'],
        seller_id=state['seller_id'],
        round_num=state['current_round'],
        negotiation_history=history_strings
    )

    if decision.action == NegotiationAction.ACCEPT:
        message_text = decision.message or f"I accepted your offer of {state['current_offer']:.2f}. Deal"
        state['status'] = 'accepted'
        state['final_price'] = state['current_offer']
    
    elif decision.action == NegotiationAction.WALK_AWAY:
        message_text = decision.message or "I am going to pass"
        state['status'] = 'walked_away'

    else:
        message_text = decision.message or f"How about ${decision.price:.2f}?"
        state['current_offer'] = decision.price

    # record message
    message = NegotiationMessage(
        round_number=state['current_round'],
        from_agent=state['buyer_id'],
        to_agent=state['seller_id'],
        price=decision.price,
        action=decision.action,
        message=message_text
    )

    state['history'].append(message)
    state['last_action'] = decision.action.value
    state['last_message'] = message_text

    print(f" Buyer: {message_text}")

    return state


def check_max_rounds(state: NegotiationState) -> NegotiationState:
    """ 
    node check maximum rounds reached
    Args:
        state: current state
    Returns:
        updated state
    """
    if state['current_round'] >= 5:
        print("\nMax round (5) reached. Negotiation failed")
        state['status'] = 'rejected'
        state['last_action'] = 'REJECT'
    return state

def finalized_success(state: NegotiationState) -> NegotiationState:
    """
    node finalize successful negotiation
    Args:
        state: current state
    Returns:
        updated state
    """
    print(f"\n{'='*60}")
    print("NEGOTIATION SUCCESSFUL!")
    print(f"{'='*60}")
    print(f"   Final price: ${state['final_price']:.2f}")
    print(f"   Rounds: {state['current_round']}")
    print(f"   Product: {state['listing'].product.name}")
    return state

def finalized_failure(state: NegotiationState) -> NegotiationState:
    """
    node finalize failed negotiation
    Args:
        state: current state
    Returns:
        updated state
    """
    print(f"\n{'='*60}")
    print("NEGOTIATION FAILED")
    print(f"{'='*60}")
    print(f"   Reason: {state['status']}")
    print(f"   Rounds: {state['current_round']}")
    
    return state







