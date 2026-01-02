"""
base agent class with LLM integration
handles communication with gemini and structured outputs
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError
from typing import Optional, Dict, List


from models.data_models import (
    AgentState,
    InventoryItem, 
    PricingDecision,
    MemoryEntry,
    Transaction, 
    Listing,
    BuyerDecision,
    NegotiationDecision,
    NegotiationAction
)

from agents.archetypes import get_personality

from config.settings import settings


class BaseAgent:
    """
    base agent with LLM powered decision
    """
    def __init__(self, state:AgentState):
        """
        initialize agent with state

        Args: 
            state: AgentState object with agent's current state
        """
        self.state = state
        self.personality = get_personality(state.archetype)
        # initialize llm 
        self.llm = ChatGoogleGenerativeAI(
            model = settings.GEMINI_MODEL,
            project = settings.PROJECT_ID,
            location = settings.LOCATION,
            temperature = settings.TEMPERATURE,
            vertexai = True            
        )

        print(f"Initialized {self.state.name} with archetype {self.state.archetype.value}")


    def _create_system_prompt(self, task_context:str) -> str:
        """
        create system prompt using the personality + task content

        Args:
            task_context: specicific instruction for current task
        
        Returns:
            complete system prompt
        """
        inventory_motivation = ""
        if len(self.state.inventory) < 2:
            inventory_motivation = " \nIMPORTANT: Your inventory is low! You need to buy items to sell later"

        return f"""You are {self.state.name} an AI trading agent in a marketplace simulations.

        {self.personality}

        IMPORTANT RULES:
        - Always respond with valid JSON only, no additional text
        - Be consistent with your personality
        - Use your memory of past interactions
        - Consider market data when making decisions
        - Stay in character
        - YOU ARE HERE TO TRADE - be active in the marketplace

        Current Status:
        - Capital: ${self.state.capital:.2f}
        - Inventory items: {len(self.state.inventory)}
        - Total sales: {self.state.total_sales}
        - Total purchases: {self.state.total_purchases}
        - Total profit so far: ${self.state.total_profit:.2f}

        {task_context}

        """
    

    def decide_pricing(
            self, 
            item: InventoryItem,
            market_avg_price: Optional[float] = None,
            ) -> PricingDecision:
        """
        agent decides how to price an item for listing
        
        Args:
            item: iventory item  to price
            market_avg_price: recent average price if available
        
        Returns:
            PricingDecision with listing_price, minimum acceptable, reasoning
        """

        # build context
        market_context = ""
        if market_avg_price:
            market_context = f"Recent market average price for {item.product.category} is: ${market_avg_price:.2f}"
        else:
            market_context = f"No recent market data available for {item.product.category}"
        
        # memory context:
        memory_context = self.get_memory_context()
        
        task_context = f"""
            TASK: Decide pricing for an item you want to sell

            Item Details:
            - Product: {item.product.name}
            - Category: {item.product.category}
            - Your cost: ${item.cost_basis:.2f}
            - Base market value: ${item.product.base_market_value:.2f}

            Market Context:
            {market_context}

            Your memory and experience:
            {memory_context}

            Decide:
            1. What price to list it at (listing_price)
            2. The minimum price you'll accept (minimum_acceptable)
            3. Your reasoning

            Remember your personality and profit requirements!
            """

        system_prompt = self._create_system_prompt(task_context)

        try:
            structured_llm = self.llm.with_structured_output(PricingDecision)
            result = structured_llm.invoke(system_prompt)

            # Ensure we have a PricingDecision object (not dict)
            decision: PricingDecision
            if isinstance(result, dict):
                decision = PricingDecision(**result)
            else:
                decision = result

            print(f" {self.state.name} pricing decision")
            print(f" List: ${decision.listing_price:.2f}")
            return decision
        
        except ValidationError as e:
            print(f" Invalide price decision from {self.state.name}: {e}")
            return PricingDecision(
                listing_price=item.cost_basis * 1.2,
                minimum_acceptable= item.cost_basis * 1.1,
                reasoning="Fallback pricing due to validation error"
            )
    

    def evaluate_listings(
            self, 
            available_listings: List,
            market_snapshot
            ) -> Optional[Dict]:
        """
        evaluate listing and decide if pursuing
        Args:
            available_listing: list of products available
            market_snapshot: current market data
        Returns:
            a dictionary with target_listings, offer_price and None
        """
        if not available_listings:
            return None
        
        print(f"AVAILABLE LISTINGS DEBUG {available_listings}")
        
        # get memory context
        memory_context = self.get_memory_context()

        # format listing for llm
        listings_text = "\n".join([
            f" - [{i+1} for {listing.product.name} ({listing.product.category})]"
            f" asking ${listing.listing_price:.2f} from {listing.seller_id}"
            for i, listing in enumerate(available_listings)
        ])

        task_context = f"""
            TASK: Evaluate available marketplace listings and decide if you want to buy anything

            Your Current State:
            - Capital available: ${self.state.capital:.2f}
            - Current inventory: {len(self.state.inventory)} items

            Available Listings:
            {listings_text}

            Market Context:
            - Active listings: {market_snapshot.active_listings_count}
            - Recent average prices by category:
        """

        # categories average
        categories = set(listing.product.category for listing in available_listings)
        for category in categories:
            avg_price = market_snapshot.get_average_price(category)
            if avg_price:
                task_context += f"\n - {category}: ${avg_price:.2f}\n"
        
        task_context += f"""
            Your Memory & Experience:
            {memory_context}

            IMPORTANT INSTRUCTIONS:
            1. You are in a marketplace to TRADE - buying and selling is how you make profit
            2. Look for opportunities where you can buy items and resell them later
            3. Consider negotiating - you don't have to pay the asking price
            4. If an item is reasonably priced and you can afford it, consider making an offer

            Decide:
            1. Do you want to make an offer on any listing? (true/false)
            2. If yes, which listing number? (1 to {len(available_listings)}) REQUIRED if interested is true
            3. What price would you offer? REQUIRED if interested is true
            4. Your reasoning

            IMPORTANT: If interested is true, you MUST provide both listing_number and offer_price.

            Consider:
            - Can you afford it?
            - Is the asking price fair based on market data?
            - Do you need this item?
            - What does your experience tell you?
            - Your personality and strategy

            Remember:
            - You can offer LESS than the asking price (this starts a negotiation)
            - Buying inventory gives you items to sell later for profit
            - Not buying means missing opportunities
            - Consider your personality: are you aggressive? opportunistic? what would your archetype do?
        """
        system_prompt = self._create_system_prompt(task_context)

        # response schema
        try:
            structured_llm = self.llm.with_structured_output(BuyerDecision)
            result = structured_llm.invoke(system_prompt)

            # DEBUG: Print raw result
            print(f"\n   🔍 RAW RESULT for {self.state.name}:")
            print(f"      Type: {type(result)}")
            print(f"      Content: {result}")
            
            decision: BuyerDecision
            if isinstance(result, dict):
                decision = BuyerDecision(**result)
            else:
                decision = result

            # DEBUG: Print parsed decision
            print("\n   🔍 PARSED DECISION:")
            print(f"      Interested: {getattr(decision, 'interested', 'ERROR')}")
            print(f"      Listing: {getattr(decision, 'listing_number', 'ERROR')}")
            print(f"      Offer: {getattr(decision, 'offer_price', 'ERROR')}")
            
            if not decision.interested or decision.listing_number is None:
                print(f" {self.state.name} decided not to buy anything")
                return None
            
            # validade listing number
            if decision.listing_number < 1 or decision.listing_number > len(available_listings):
                print(f"Invalid listing number: {decision.listing_number}")
                return None
            
            target_listing = available_listings[decision.listing_number - 1]

            # validade offer price
            if decision.offer_price is None or decision.offer_price <= 0:
                print(f"Invalid offer price: {decision.offer_price}")
                return None
            
            # check aforrdability
            if decision.offer_price > self.state.capital:
                print(f" {self.state.name} cannot afford ${decision.offer_price:.2f}")
                return None

            print(f" {self.state.name} is instereted in buy {target_listing.product.name}")
            print(f" Offer price: ${decision.offer_price:.2f}")
            print(f" Reasoning: {decision.reasoning}")
            
            return {
                "listing": target_listing,
                "offer_price": decision.offer_price,
                "reasoning": decision.reasoning
            }
        
        except Exception as e:
            print(f"Evaluation failed for {self.state.name}: {e}")
            return None



####################################
    # NEGOTIATION METHODS
####################################

    def evaluate_offer_as_seller(
            self, 
            offer_price: float,
            cost_basis: float,
            listing_price: float,
            minimum_acceptable: float,
            buyer_id: str,
            round_num: int,
            negotiation_history: List[str]
        ):
        """
        Seller evaluates a buyer's offer and decide how to respond
        
        :param self: Descrição
        :param offer_price: buyer offer
        :type offer_price: float
        :param cost_bassis: cost to the seller
        :type cost_bassis: float
        :param listing_price: price asked
        :type listing_price: float
        :param minimum_acceptable: minimum acceptable price
        :type minimum_acceptable: float
        :param buyer_id: buyer id
        :type buyer_id: str
        :param round_num: round of the negotiation, max 
        :param negotiation_history: list of what's been said in the negotiation
        :type negotiation_history: List[str]
        """
        # get memory about this buyer
        memory_context = self.get_memory_context(buyer_id)

        # format negotiation history
        history_text = "\n".join(negotiation_history) if negotiation_history else "No previous messages"

        # calculate potential profit
        potential_profit = offer_price - cost_basis
        potential_margin = (potential_profit / cost_basis) * 100
        
        task_context = f"""
        TASK: Evaluate a buyer's offer for an item you're selling

        Your Item:
        - Your cost basis: ${cost_basis:.2f}
        - Your listing price: ${listing_price:.2f}
        - Your stated minimum: ${minimum_acceptable:.2f}

        Buyer's Offer:
        - Offered price: ${offer_price:.2f}
        - From: {buyer_id}

        Analysis:
        - Potential profit: ${potential_profit:.2f}
        - Potential margin: {potential_margin:.1f}%
        - Offer vs listing: {((offer_price/listing_price - 1) * 100):+.1f}%
        - Offer vs minimum: {((offer_price/minimum_acceptable - 1) * 100):+.1f}%

        Negotiation Context:
        - Current round: {round_num} of 5
        - History:
        {history_text}

        What you know about {buyer_id}:
        {memory_context}

        Your Memory & Experience:
        {self.get_memory_context()}

        Decide your response:
        1. ACCEPT - Take the offer (negotiation ends successfully)
        2. REJECT - Refuse the offer (negotiation ends, no deal)
        3. COUNTER - Make a counter-offer (negotiation continues)

        If you COUNTER, decide:
        - What price to counter with
        - What message to send to persuade them

        Important considerations:
        - Round {round_num} of 5 (limited time!)
        - Your personality and strategy
        - Is this profit acceptable?
        - Can you get more, or should you take it?
        - If you counter, will they walk away?
        """

        system_prompt = self._create_system_prompt(task_context)

        try:
            structure_llm = self.llm.with_structured_output(NegotiationDecision)
            result = structure_llm.invoke(system_prompt)
            
            decision: NegotiationDecision
            if isinstance(result, dict):
                decision = NegotiationDecision(**result)
            else:
                decision = result
            
            # log decision
            action_text = decision.action.value
            if decision.action == NegotiationAction.COUNTER and decision.price:
                print(f" {self.state.name} (seller) {action_text} at ${decision.price:.2f}")
            else:
                print(f" {self.state.name} (seller) {action_text}")
            
            return decision
            
        except Exception as e:
            print(f" Seller evaluation failed for {self.state.name}: {e}")
            # fallback: accept above minumum
            if offer_price > minimum_acceptable:
                return NegotiationDecision(
                    action=NegotiationAction.ACCEPT, 
                    reasoning="Fallback decision, offer meets minimum")
            else:
                return NegotiationDecision(
                    action=NegotiationAction.REJECT, 
                    reasoning="Fallback decision, offer does not meet minimum")
            
            
    def evaluate_counter_as_buyer(
            self, 
            counter_price:float,
            my_last_offer: float,
            listing: "Listing",
            seller_id: str,
            round_num: int,
            negotiation_history: List[str]
        ):
        """
        Buyer evaluates counter proposal
        
        :param self: Descrição
        :param counter_offer: counter offer
        :type counter_price: float
        :param my_last_offer: last offer
        :type my_last_offer: float
        :param listing: the listing being negotiated
        :type listing: "Listing"
        :param seller_id: seller id
        :type seller_id: str
        :param round_num: round of negotiation
        :type round_num: int
        :param negotiation_history: everything being said in negotiation
        :type negotiation_history: List[str]
        """
        memory_context = self.get_memory_context(seller_id)

        # format negotiation history
        history_text = "\n".join(negotiation_history) if negotiation_history else "No previous messages"

        # calculate if affordable
        can_afford = counter_price is not None and self.state.capital >= counter_price
        
        task_context = f"""
        TASK: Evaluate a seller's counter offer for an item you're buying

        The Item:
        - Product: {listing.product.name}
        - Category: {listing.product.category}
        - Original asking price: ${listing.listing_price:.2f}

        Seller's Counter:
        - Counter price: ${counter_price:.2f}
        - From: {seller_id}

        Your Situation:
        - Your last offer: ${my_last_offer:.2f}
        - Your capital: ${self.state.capital:.2f}
        - Can afford counter: {"Yes" if can_afford else "No"}

        Analysis:
        - Counter vs your offer: {((counter_price/my_last_offer - 1) * 100):+.1f}%
        - Counter vs original: {((counter_price/listing.listing_price - 1) * 100):+.1f}%
        - Seller came down: ${listing.listing_price - counter_price:.2f}

        Negotiation Context:
        - Current round: {round_num} of 5
        - History:
        {history_text}

        What you know about {seller_id}:
        {memory_context}

        Your Memory & Experience:
        {self.get_memory_context()}

        Decide your response:
        1. ACCEPT - Accept the counter-offer (get the item at this price)
        2. WALK_AWAY - Reject and end negotiation (no deal)
        3. COUNTER - Make another counter-offer (negotiation continues)

        If you COUNTER, decide:
        - What price to counter with (must be <= ${self.state.capital:.2f})
        - What message to send to persuade them

        Important considerations:
        - Round {round_num} of 5 (limited time!)
        - Your personality and strategy
        - Is this price worth it?
        - Can you negotiate lower, or should you accept?
        - Do you even need this item?
        """

        system_prompt = self._create_system_prompt(task_context)

        try:
            structure_llm = self.llm.with_structured_output(NegotiationDecision)
            result = structure_llm.invoke(system_prompt)

            decision: NegotiationDecision
            if isinstance(result, dict):
                decision = NegotiationDecision(**result)
            else:
                decision = result
            
            # validade counter price
            if decision.action == NegotiationAction.COUNTER:
                if decision.price is None or decision.price > self.state.capital:
                    print(f" {self.state.name} cannot afford counter offer of ${decision.price:.2f}")
                    decision.action = NegotiationAction.WALK_AWAY
                    decision.price = None
                elif decision.price <= 0:
                    print(f" {self.state.name} invalid counter price: {decision.price}")
                    decision.action = NegotiationAction.WALK_AWAY
                    decision.price = None
            
            # log decision
            action_text = decision.action.value
            if decision.action == NegotiationAction.COUNTER and decision.price:
                print(f" {self.state.name} (seller) {action_text} at ${decision.price:.2f}")
            else:
                print(f" {self.state.name} (seller) {action_text}")
            
            return decision
            
        except Exception as e:
            print(f" Buyer's evaluation failed for {self.state.name}: {e}")
            # fallback: walk away
            return NegotiationDecision(
                action=NegotiationAction.WALK_AWAY, 
                reasoning="Fallback decision, evaluation error")
    


####################################
    # MEMORY METHODS
####################################

    def add_transaction_memory(self, transaction):
        """
        add a complete transaction memory to agents
        
        Args:
            transaction: complete transaction to remember
        """
        # role
        is_seller = (transaction.seller_id == self.state.agent_id)

        # update stats
        if is_seller:
            self.state.total_sales += 1
            self.state.total_profit += transaction.profit
        else:
            self.state.total_purchases += 1
        
        # store in memory
        self.state.memory.add_transaction(transaction)

        # add important events
        importance = self._calculate_event_importance(transaction)

        event = MemoryEntry(
            event_type="transaction",
            description=self._describe_transaction(transaction),
            importance=importance,
            related_agent=(
                transaction.buyer_id if transaction.seller_id == self.state.agent_id else transaction.seller_id
            )
        )
        self.state.memory.add_event(event)

        print(f' {self.state.name} added transaction memory, importance: {importance:.2f}')

    
    def _calculate_event_importance(self, transaction)->float:
        """
        calculate how important a transaction is 0.0 - 1.0
        based on profit, margin, deal size, 
        
        Args:
            transaction: transaction to evaluate
        
        Returns:
            importante score from 0.0 to 1.0
        """
        if not isinstance(transaction, Transaction):
            return 0.5
        
        # base importance
        importance = 0.5

        # high profit more imporance
        if transaction.margin > 25:
            importance += 0.3
        elif transaction.margin > 15:
            importance += 0.1
        elif transaction.margin < 5:
            importance += 0.2
        
        # large transaction
        if transaction.final_price > 1000:
            importance += 0.2

        # cap at 1.0
        return min(importance, 1.0)

    
    def _describe_transaction(self, transaction) -> str:
        """
        create description of transaction
        Args:
            transaction: transaction to describe
        
        Returns:
            description of transaction
        """
        if transaction.seller_id == self.state.agent_id:
            return(
                f"Sold: {transaction.product.name} for ${transaction.final_price:.2f} "
                f"Cost: ${transaction.cost_basis:.2f}, profit: ${transaction.profit:.2f}"
                f"Margin: ${transaction.margin:.2f} to {transaction.buyer_id}"                
            )
        else:
            return(
                f"Bought {transaction.product.name} for {transaction.final_price:.2f} "
                f"From {transaction.seller_id}"
            )
        
    
    def add_negotiation_failure(self, other_agent_id:str, reason:str):
        """
        record failed negotiation
        Args:
            other_agent_id: id of other agent
            reason: reason for failure
        """
        event = MemoryEntry(
            event_type="negotiation_failure",
            description=f"Failed negotiation with {other_agent_id}: {reason}",
            importance=0.6,
            related_agent=other_agent_id
        )
        self.state.memory.add_event(event)

        # update  learned patterns
        current_pattern = self.state.memory.learned_patterns.get(other_agent_id, '')
        if "difficult" not in current_pattern.lower():
            self.state.memory.learned_patterns['other_agent_id'] = (
                current_pattern + " Difficult negotiator " if current_pattern else " Difficult negotiator"
            )


    def learn_pattern(self, other_agent_id:str, pattern:str):
        """
        learn pattern about other agent
        Args:
            other_agent_id: id of other agent
            pattern: pattern to learn
        """
        self.state.memory.learned_patterns[other_agent_id] = pattern
        print(f"{self.state.name} learned pattern from {other_agent_id}: {pattern}")

    
    def update_memory_summary(self):
        """
        update high level summary of agent's experience
        """
        total_transactions = self.state.total_sales + self.state.total_purchases
        
        if total_transactions == 0:
            self.state.memory.summary = "No transactions yet"
            return
        
        avg_profit = (self.state.total_profit / total_transactions if self.state.total_sales > 0 else 0)

        # find best category
        category_performance = {}

        # analysing best perforamnce for sold items
        for txn in self.state.memory.recent_transactions:
            if txn.seller_id == self.state.agent_id:           
                cat = txn.product.category
                if cat not in category_performance:
                    category_performance[cat] = []
                category_performance[cat].append(txn.margin)
        
        best_category = None
        best_margin = 0
        if category_performance:
            for cat, margin in category_performance.items():
                avg_margin = sum(margin) / len(margin)
                if avg_margin > best_margin:
                    best_category = cat 
                    best_margin = avg_margin
        
        summary_parts = [
            f"Completed {total_transactions} transactions",      
        ]


        if self.state.total_sales > 0 and self.state.total_purchases > 0:   
            summary_parts.append(f"{self.state.total_sales} sales, {self.state.total_purchases} purchases")
        elif self.state.total_sales > 0:
            summary_parts.append(f"{self.state.total_sales} sales")
        elif self.state.total_purchases > 0:
            summary_parts.append(f"(all {self.state.total_purchases} purchases)")
        
        # add profit if sales
        if self.state.total_sales > 0:
            summary_parts.append(f"Average profit per sale: ${avg_profit:.2f}")
        

        if best_category:
            summary_parts.append(
                f"Best category {best_category} with average margin: {best_margin:.2f}"
            )

        self.state.memory.summary = " ".join(summary_parts)
        print(f"{self.state.name} updated memory summary: {self.state.memory.summary}")

    
    def get_memory_context(self, about_agent:Optional[str] = None) ->str:
        """
        get relevant memory context to include LLM prompt
        Args:
            about_agent: if provided include memory about this agent
        Return:
            formated string with memory context
        """
        context_parts = []

        # add summary
        if self.state.memory.summary:
            context_parts.append(f"Your experience summary {self.state.memory.summary}")
        
        # add recent transactions
        if self.state.memory.recent_transactions:
            context_parts.append("\nRecent transactions:")
            for txn in self.state.memory.recent_transactions:
                context_parts.append(f" - {self._describe_transaction(txn)}")
        
        # add relevant learned patters
        if about_agent and about_agent in self.state.memory.learned_patterns:
            context_parts.append(
                f"\nWhat you know about {about_agent}: {self.state.memory.learned_patterns[about_agent]}"
            )
        elif self.state.memory.learned_patterns:
            context_parts.append("\nPatterns you've learned:")
            for agent_id, pattern in list(self.state.memory.learned_patterns.items()):
                context_parts.append(f" - {agent_id}: {pattern}")
        
        # add important events
        important_events = sorted(
            self.state.memory.important_events, key=lambda x: x.importance, reverse=True
        )[:3]

        if important_events:
            context_parts.append("\nImportant events:")
            for event in important_events:
                context_parts.append(f" - {event.description} (importance: {event.importance:.2f})")
        
        return "\n".join(context_parts) if context_parts else "No memory available"

    
    def __repr__(self) -> str:
        """
        String representation of the agent
        """
        return (
            f"Agent {self.state.name} with archetype {self.state.archetype.value} | "
            f"Capital: ${self.state.capital:.2f} | "
            f"Inventory items: {len(self.state.inventory)} items) "
        )

        

    




        