"""
marketplace for trading agents
listing, negotiation, transaction
"""
from typing import List, Dict, Optional
from datetime import datetime
import uuid

from models.data_models import Listing, Product, MarketSnapshot, Transaction

class Marketplace:
    """
    manages listings, negotiations and transactions
    """
    def __init__(self):
        self.active_listings: Dict[str, Listing] = {}
        self.removed_listings: List[Listing] = []
        self.completed_transactions: List[Transaction] = []

        print("Marketplace initialized")

    def post_listing(
            self, 
            seller_id: str, 
            product: Product, 
            listing_price: float, 
            minimum_acceptable: float, 
            reasoning: str) -> Listing:
        """
        create a new listing in the marketplace
        """
        listing = Listing(
            listing_id=f"listing_{uuid.uuid4().hex[:8]}",
            seller_id=seller_id,
            product=product,
            listing_price=listing_price,
            minimum_acceptable=minimum_acceptable,
            reasoning=reasoning
        )

        self.active_listings[listing.listing_id] = listing
        print(f"New listing posted: {product.name} by {seller_id} for ${listing_price:.2f}")
        
        return listing

    def get_all_listings(self) -> List[Listing]:
        """
        get all listings in the marketplace
        """
        return list(self.active_listings.values())
    
    
    def get_listings_by_category(self, category: str) -> List[Listing]:
        """
        get all listings for a specific category
        """
        return [listing for listing in self.active_listings.values() if listing.product.category == category]

 
    def get_listings_excluding_seller(self, seller_id: str) -> List[Listing]:
        """
        get all listings excluding a specific seller
        """
        return [listing for listing in self.active_listings.values() if listing.seller_id != seller_id]


    def get_listing(self, listing_id: str) -> Listing:
        """
        get a listing by its ID
        """
        return self.active_listings.get(listing_id)
    

    def remove_listing(self, listing_id: str):
        """
        remove a listing from the marketplace
        """
        if listing_id in self.active_listings:
            listing = self.active_listings.pop(listing_id)
            self.removed_listings.append(listing)
            print(f"Removed listing {listing.product.name} with ID {listing_id} removed.")
            return True
        return False
    

    def record_transaction(self, transaction: Transaction):
        """
        record a completed transaction
        """
        self.completed_transactions.append(transaction)
        print(f"Transaction recorded: {transaction.product.name} sold for ${transaction.final_price:.2f}")



    def get_market_snapshot(self) -> MarketSnapshot:
        """
        get a snapshot of the current market conditions
        """
        recent = self.completed_transactions[-20:] if self.completed_transactions else []
        snapshot = MarketSnapshot(
            active_listings_count=len(self.active_listings),
            recent_transactions=recent
        )
        return snapshot
    
    def get_average_price(self, category: Optional[str]=None) -> Optional[float]:
        """
        get the average price of a product category
        """
        snapshot = self.get_market_snapshot()
        return snapshot.get_average_price(category)
    

    def get_price_trend(self, product_category: str)->Optional[str]:
        """
        get the price trends of a product category(rising, falling, stable)
        """
        snapshot = self.get_market_snapshot()
        return snapshot.get_price_trend(product_category)


    def get_statistics(self)->Dict:
        """
        get marketplace statistics
        """
        total_volume = sum(txn.final_price for txn in self.completed_transactions)
        avg_transaction = (total_volume / len(self.completed_transactions) if self.completed_transactions else 0)
        return {
            "active_listings": len(self.active_listings),
            "total_transactions": len(self.completed_transactions),
            "total_volume": total_volume,
            "average_transaction": avg_transaction,
            "categories_listed":len(set(listing.product.category for listing in self.active_listings.values()))
        }

    
    def __repr__(self) -> str:
        """
        string representation of the marketplace
        """
        return (f"Marketplace with {len(self.active_listings)} active listings,"
                f" transactions: {len(self.completed_transactions)}")
    

    


    

    