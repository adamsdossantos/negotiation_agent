"""
simlation testing
tests the entire system 
"""
from market.coordinator import MarketCoordinator
from market.analytics import MarketAnalytics


def test_full_autonomous_simulation():
    """Test full simulation with only AI agents"""
    print("\n" + "="*70)
    print("FULL AUTONOMOUS SIMULATION TEST")
    print("="*70)
    
    # Create coordinator with 7 agents
    coordinator = MarketCoordinator(num_agents=10)
    
    # Run simulation
    coordinator.run_simulation(num_cycles=5)
    
    # Generate analytics
    analytics = MarketAnalytics(coordinator)
    analytics.print_report()
    
    print("\n Full autonomous simulation complete!")


def test_user_participation():
    """Test simulation with user participation"""
    print("\n" + "="*70)
    print("USER PARTICIPATION TEST")
    print("="*70)
    
    # Create coordinator
    coordinator = MarketCoordinator(num_agents=5)
    coordinator.initialize_agents()
    
    # Create user agent
    user = UserAgent(name="TestUser", capital=3000.0)
    coordinator.agents[user.state.agent_id] = user
    
    # Run one cycle
    print("\n🤖 AI agents listing items...")
    coordinator.run_listing_phase()
    

if __name__ == "__main__":
    test_full_autonomous_simulation()
    
