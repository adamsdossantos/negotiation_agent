"""
Analytics and metrics 
reports on agents performances
"""
from typing import Dict
from market.coordinator import MarketCoordinator

class MarketAnalytics:
    """ 
    Calculate and display metrics
    """
    def __init__(self, coordinator: MarketCoordinator):
        self.coordinator = coordinator
        self.marketplace = coordinator.marketplace
        self.agents = coordinator.agents

    def calculate_metrics(self) -> Dict:
        """
        calculate and return metrics
        """
        transactions = self.marketplace.completed_transactions

        if not transactions:
            return {
                "error": "No transactions to analyze"
            }

        # transaction volume
        total_volume = sum(txn.final_price for txn in transactions)
        transaction_count = len(transactions)
        avg_transaction = total_volume / transaction_count if transaction_count > 0 else 0

        # cost of goods
        total_cogs = sum(txn.cost_basis for txn in transactions)

        # profit metrics
        total_profit = sum(txn.profit for txn in transactions)
        margins = [txn.margin for txn in transactions]
        avg_margin = sum(margins) / len(transactions) if margins else 0
        min_margin = min(margins) if margins else 0
        max_margin = max(margins) if margins else 0

        # price stability per cat
        categories = {}
        for txn in transactions:
            cat = txn.product.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(txn.final_price)
        
        price_stability = {}
        for cat, prices in categories.items():
            if len(prices) > 1:
                avg_prices = sum(prices) / len(prices)  
                variance = sum((price - avg_prices) ** 2 for price in prices) / (len(prices))
                std_dev = variance ** 0.5
                variance_pct = (std_dev / avg_prices * 100) if avg_prices > 0 else 0
                price_stability[cat] = {
                    "avg_price": avg_prices,
                    "std_dev": std_dev,
                    "variance_pct": variance_pct,
                    "count": len(prices)
                }
        
        # agents performance
        agent_stats ={}
        for agent_id, agent in self.agents.items():
            agent_stats[agent_id] = {
                "name": agent.state.name,
                "archetype": agent.state.archetype.value,
                "capital": agent.state.capital, 
                "final_capital": agent.state.capital,
                "total_sales": agent.state.total_sales,
                "total_purchases": agent.state.total_purchases,
                "total_profit": agent.state.total_profit,
                "avg_profit_per_sale": (
                    agent.state.total_profit / agent.state.total_sales 
                    if agent.state.total_sales > 0 else 0)
            }
        
        # find top performers
        sort_by_profit = sorted(
            agent_stats.items(), 
            key=lambda x: x[1]['total_profit'], 
            reverse=True
            )
        
        sorted_by_capital = sorted(
            agent_stats.items(),
            key=lambda x: x[1]['final_capital'],
            reverse=True
        )

        return {
            "transaction_volume":{
                "total_transactions": transaction_count,
                "total_volume": total_volume,
                "avg_transaction": avg_transaction,
            },
            "cost_metrics":{
                "total_cogs": total_cogs,
                "total_profit": total_profit,
                "avg_margin":avg_margin,
                "min_margin": min_margin,
                "max_margin": max_margin,
            },
            "price_stability": price_stability,
            "agents_performance": agent_stats,
            "top_by_profit": sort_by_profit[:5],
            "top_by_capital": sorted_by_capital[:5]
        }
    

    def print_report(self):
        """
        print the report
        """
        metrics = self.calculate_metrics()

        if "error" in metrics:
            print(metrics["error"])
            return

        print(f"\n{'='*60}")
        print(" MARKETPLACE ANALYTICS REPORT")
        print(f"{'='*60}")

        # Transaction Volume
        print("\nTRANSACTION VOLUME")
        print(f"{'='*60}")
        vol = metrics["transaction_volume"]
        print(f"Total Transactions:     {vol['total_transactions']}")
        print(f"Total Volume:           ${vol['total_volume']:,.2f}")
        print(f"Average Transaction:    ${vol['avg_transaction']:,.2f}")
        
        # Cost & Profit
        print("\n COST & PROFIT METRICS")
        print(f"{'='*60}")
        cost = metrics["cost_metrics"]
        print(f"Total COGS:             ${cost['total_cogs']:,.2f}")
        print(f"Total Profit:           ${cost['total_profit']:,.2f}")
        print(f"Average Margin:         {cost['avg_margin']:.2f}%")
        print(f"Margin Range:           {cost['min_margin']:.2f}% - {cost['max_margin']:.2f}%")
        
        # Price Stability
        print("\n PRICE STABILITY BY CATEGORY")
        print(f"{'='*60}")
        for cat, stats in metrics["price_stability"].items():
            print(f"\n{cat}:")
            print(f"  Average Price:    ${stats['avg_price']:,.2f}")
            print(f"  Std Deviation:    ${stats['std_dev']:,.2f}")
            print(f"  Variance:         {stats['variance_pct']:.2f}%")
            print(f"  Transactions:     {stats['count']}")
        
        # Top Performers
        print("\n TOP PERFORMERS (by Profit)")
        print(f"{'='*60}")
        for i, (agent_id, stats) in enumerate(metrics["top_by_profit"], 1):
            print(f"\n#{i} {stats['name']} ({stats['archetype']})")
            print(f"    Total Profit:         ${stats['total_profit']:,.2f}")
            print(f"    Sales:                {stats['total_sales']}")
            print(f"    Avg Profit/Sale:      ${stats['avg_profit_per_sale']:,.2f}")
            print(f"    Final Capital:        ${stats['final_capital']:,.2f}")
        
        # Agent Summary
        print("\n ALL AGENTS SUMMARY")
        print(f"{'='*60}")
        for agent_id, stats in metrics["agents_performance"].items():
            print(f"\n{stats['name']} ({stats['archetype']})")
            print(f"  Capital:      ${stats['final_capital']:,.2f}")
            print(f"  Sales:        {stats['total_sales']}")
            print(f"  Purchases:    {stats['total_purchases']}")
            print(f"  Profit:       ${stats['total_profit']:,.2f}")


        print(f"\n{'-'*60}")
        print(" END OF REPORT")
        print(f"{'='*60}")

