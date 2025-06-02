# train_ml_model.py
import asyncio
import logging
from ml_model import MLModel
from database import Database

logging.basicConfig(level=logging.INFO)

async def train_model():
    """Train the ML model with current trading data"""
    
    db = Database(db_path='data/sol_bot.db')
    ml_model = MLModel()
    
    print("🤖 Training ML Model...")
    
    # Train the model
    success = ml_model.train(db)
    
    if success:
        print("✅ ML Model trained successfully!")
        
        # Get performance stats
        stats = ml_model.get_performance_stats()
        print(f"\nModel Performance:")
        print(f"  Accuracy: {stats['accuracy']*100:.1f}%")
        print(f"  Precision: {stats['precision']*100:.1f}%")
        print(f"  Training samples: {stats['training_samples']}")
        
        # Show feature importance
        if stats.get('feature_importance'):
            print(f"\nTop Features:")
            for feature, importance in sorted(stats['feature_importance'].items(), 
                                            key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {feature}: {importance:.3f}")
    else:
        print("❌ Not enough data to train model yet")
        print("   Continue trading to collect more data")

if __name__ == "__main__":
    asyncio.run(train_model())