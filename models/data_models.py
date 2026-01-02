"""
core data models for marketplace simulation
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal
from datetime import datetime
from enum import Enum

# enum define valid choices
class NegotiationAction(str, Enum):
    """ 
    valid action in negotiation
    """
    MAKE_OFFER = 'MAKE_OFFER'
    ACCEPT= 'ACCEPT'
    REJECT= 'REJECT'
    COUNTER= 'COUNTER'
    WALK_AWAY= 'WALK_AWAY'

class AgentArchetype(str, Enum):
    """
    agent personalities
    """
    AGGRESSIVE_TRADER = 'Agressive_Trader'
    PATIENT_INVESTOR = 'Patient_Investor'
    OPPORTUNIST = 'Opportunist'
    RISK_TAKER = 'Risk_Taker'
    CONSERVATIVE = 'Conservative'
    SPECIALIST = 'Specialist'
    EMOTIONAL = 'Emotional'
    DATA_DRIVEN = 'Data_Driven'
    SOCIAL = 'Social'
    CHAOTIC = 'Chaotic'

# product models
class Product(BaseModel):
    """
    represent a product in the marketplace
    """
    name: str = Field(..., min_length=1, description='product name..')
    category: str = Field(..., min_length=1, description='e.g. eletronics')
    base_market_value: float = Field(..., gt=0)
    
    model_config = {'frozen': True} # products are immutable
   

class InventoryItem(BaseModel):
    """
    represents an item in agents inventory
    """
    product: Product # shouldnt it be a list of products?
    cost_basis: float = Field(..., gt=0, description='what the agent paid for the product')
    acquired_at: datetime = Field(default_factory=datetime.now)

    @field_validator('cost_basis')
    @classmethod
    def cost_must_be_reasonable(cls, v:float, info)->float:
        """
        validade the cost is within reasonable bounds
        """
        product = info.data.get('product')
        if product:
            # cost should be between 50% and 100% of market value
            if v < product.base_market_value * 0.5:
                raise ValueError(f'cost is too low {v}')
            
            if v > product.base_market_value * 1.0:
                raise ValueError(f'cost is too high {v}')
        return v

# listing models
class Listing(BaseModel):
    """
    represent a listing in the marketplace
    """
    listing_id: str = Field(..., min_length=1, description='unique identifier')
    seller_id: str = Field(..., min_length=1, description='seller agent id')
    product: Product
    listing_price: float = Field(..., gt=0, description='asking price')
    minimum_acceptable: float = Field(..., gt=0, description='minimum acceptable price')
    listed_at: datetime = Field(default_factory=datetime.now)
    reasoning: str = Field(..., min_length=1, description='seller reasoning for price')

    @field_validator('minimum_acceptable')
    @classmethod
    def min_acceptable_must_be_less_than_listing(cls, v:float, info)->float:
        """
        minimum is not higher than listing price 
        """
        listing_price = info.data.get('listing_price')
        if listing_price and v > listing_price:
            raise ValueError(f'minimum acceptable price {v:.2f} cannot exceed listing price{listing_price:.2f}')
        return v

# transaction models
class Transaction(BaseModel):
    """
    represents a complete trade
    """
    transaction_id: str = Field(..., min_length=1, description='unique identifier')
    buyer_id: str = Field(..., min_length=1, description='buyer agent id')
    seller_id: str = Field(..., min_length=1, description='seller agent id')
    product: Product
    final_price: float = Field(..., gt=0, description='agreed price')
    cost_basis: float = Field(..., gt=0, description='what the agent paid for the product')
    timestamp: datetime = Field(default_factory=datetime.now)
    negotiation_rounds: int = Field(..., gt=0, le=5, description='number of negotiation rounds')

    @property
    def profit(self)-> float:
        """
        calculate seller profit
        """
        return self.final_price - self.cost_basis
    
    @property
    def margin(self)-> float:
        """
        calculate seller profit percentage
        """
        return self.profit / self.cost_basis * 100

# model memory
class MemoryEntry(BaseModel):
    """
    represent the LLM memory of an agent
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str = Field(..., description='type of event, e.g. trade, negotiation_failed')
    description: str = Field(..., description='what happened')
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description='how important this memory is')
    related_agent: Optional[str] = Field(None, description='other agent involved')
    
    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%H:%M')}] {self.description}"

class AgentMemory(BaseModel):
    """
    memory of an agent
    """
    summary: str = Field(default="", description='high level summary of agent experience')
    recent_transactions: List[Transaction] = Field(default_factory=list, max_length=5)
    important_events: List[MemoryEntry] = Field(default_factory=list, max_length=10)
    learned_patterns: Dict[str, str] = Field(
        default_factory=dict, 
        description="learned patterns e.g {'Agent_3':'tough negotiator'}"
        )
    
    def add_transaction(self, transaction: Transaction):
        """ 
        add a transaction to the agent memory, last 5 ones
        """
        self.recent_transactions.append(transaction)
        if len(self.recent_transactions) > 5:
            self.recent_transactions.pop(0)
    
    def add_event(self, event: MemoryEntry):
        """ 
        add an event to the agent memory, last 10 ones
        """
        self.important_events.append(event)
        if len(self.important_events) > 10:
            self.important_events.sort(key=lambda x: x.importance, reverse=True)
            self.important_events = self.important_events[:10]

# agent state model
class AgentState(BaseModel):
    """
    represent the state of an agent
    """
    agent_id: str = Field(...,description='unique identifier')
    name: str = Field(..., min_length=1, description='agent name')
    archetype: AgentArchetype = Field(..., description='agent personality')
    # financial state
    capital: float = Field(..., gt=0, description='available cash')
    inventory: List[InventoryItem] = Field(default_factory=list)
    # memory
    memory: AgentMemory = Field(default_factory=lambda: AgentMemory())
    # stats
    total_sales: int = Field(0, ge=0)
    total_purchases: int = Field(0, ge=0)
    total_profit: float = Field(0, ge=0)

    @property
    def inventory_value(self)-> float:
        """
        calculate inventory value
        """
        return sum(item.cost_basis for item in self.inventory)
    
    @property
    def total_assets(self)-> float:
        """
        calculate inventory value + capital
        """
        return self.capital + self.inventory_value
    

    def can_afford(self, price: float)-> bool:
        """
        check if the agent can afford the purchase
        """
        return self.capital >= price
    

    def has_product_type(self, product_category: str):
        """
        check if the agent has a product of the given category
        """
        return any(item.product.category == product_category for item in self.inventory)


# negotiation model
class NegotiationMessage(BaseModel):
    """
    single message in a negotiation
    """
    round_number: int = Field(..., gt=0, le=5)
    from_agent: str = Field(..., min_length=1, description='agent id sending message')
    to_agent: str = Field(..., min_length=1, description='agent id receiving message')
    action: NegotiationAction
    price: Optional[float] = Field(None, gt=0, description='offer/counter offer')
    message: str = Field(..., min_length=1, description='persuasive message from agent')
    timestamp: datetime = Field(default_factory=datetime.now)

class NegotiateState(BaseModel):
    """
    state of a negotiation
    """
    negotiation_id: str = Field(..., min_length=1, description='unique identifier')
    listing: Listing
    buyer_id: str
    current_round: int = Field(1, gt=0, le=5)
    history: List[NegotiationMessage] = Field(default_factory=list)
    status: Literal["active", "accepted", "rejected", "walked_away"] = "active"
    final_price: Optional[float] = None

    @property
    def is_completed(self)-> bool:
        """
        check if the negotiation is completed
        """
        return self.status != 'active' or self.current_round > 5


# market data models
class MarketSnapshot(BaseModel):
    """
    snapshot in a point in time
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    active_listings_count: int = Field(default=0, ge=0)
    recent_transactions: List[Transaction] = Field(default_factory=list)
    
    def get_average_price(self, product_category: Optional[str]=None) -> Optional[float]:
        """
        get the average price of a product category
        """
        if not self.recent_transactions:
            return None

        relevant_transactions = self.recent_transactions
        if product_category:
            relevant_transactions = [
                transaction for transaction in self.recent_transactions if transaction.product.category == product_category
            ]
        
        if not relevant_transactions:
            return None 
        
        total_price = sum(transaction.final_price for transaction in relevant_transactions)
        return total_price / len(relevant_transactions)

    def get_price_trend(self, product_category: str)->Optional[str]:
        """
        get the price trends of a product category(rising, falling, stable)
        """
        category_transactions = [
            t for t in self.recent_transactions if t.product.category == product_category
        ]

        if len(category_transactions) < 3:
            return None
        
        # compare first half and second half
        mid = len(category_transactions) // 2
        first_half_average = sum(t.final_price for t in category_transactions[:mid]) / mid
        second_half_average = sum(t.final_price for t in category_transactions[mid:]) / len(category_transactions) - mid

        diff_pct = ((second_half_average - first_half_average)/first_half_average) * 100

        if diff_pct > 5:
            return 'rising'
        if diff_pct < -5:
            return 'falling'
        else:
            return 'stable'
    
# price decision models
class PricingDecision(BaseModel):
    """
    agent's decision on how to set a price
    """
    listing_price: float = Field(..., gt=0)
    minimum_acceptable: float = Field(..., gt=0)
    reasoning:str = Field(..., min_length=10)

    @field_validator('minimum_acceptable')
    @classmethod
    def validate_minimum(cls, v: float, info) -> float:
        listing = info.data.get('listing_price')
        if listing and v > listing:
            raise ValueError('minimum cannot exceed listing price')
        return v

class NegotiationDecision(BaseModel):
    """
    agent's decision during negociation
    """
    action: NegotiationAction
    price: Optional[float] = Field(None, gt=0)
    message: str = Field(default="")
    reasoning: str = Field(min_length=10, description='internal agent reasoning')

    @field_validator('price')
    @classmethod
    def price_required_for_counter(cls, v:Optional[float], info)->Optional[float]:
        action = info.data.get('action')
        if action == NegotiationAction.COUNTER and v is None:
            raise ValueError('Price required when action is counter')
        return v


class BuyerDecision(BaseModel):
    interested: bool = Field(..., description="Whether you want to make an offer")
    listing_number: Optional[int] = Field(None, description="Which listing (1-indexed)")
    offer_price: Optional[float] = Field(None, description="Your initial offer price")
    reasoning: str = Field(..., description="Your reasoning")
