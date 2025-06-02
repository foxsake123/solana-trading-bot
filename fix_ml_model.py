# fix_ml_model.py
import os
import shutil

def fix_ml_model():
    """Update ML model to use correct features"""
    
    # Backup original
    if os.path.exists('ml_model.py'):
        shutil.copy('ml_model.py', 'ml_model.py.bak')
        print("✅ Backed up original ml_model.py")
    
    # Update the features list in ml_model.py
    with open('ml_model.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the features list
    old_features = '''self.features = [
            'volume_24h', 'liquidity_usd', 'price_change_24h', 
            'price_change_6h', 'price_change_1h', 'holders',
            'social_media_score', 'safety_score'
        ]'''
    
    new_features = '''self.features = [
            'volume_24h', 'liquidity_usd', 'price_usd',
            'mcap', 'holders', 'safety_score'
        ]'''
    
    content = content.replace(old_features, new_features)
    
    # Also update the prepare_features method to handle missing columns better
    if 'def prepare_features(self, token_data):' in content:
        # Add better error handling
        old_method = '''def prepare_features(self, token_data):
        """
        Prepare features for prediction
        
        :param token_data: Token data dictionary or DataFrame row
        :return: Prepared features as numpy array
        """
        features = []
        
        # Handle both dictionary and DataFrame row input
        if isinstance(token_data, dict):
            for feature in self.features:
                value = token_data.get(feature, 0.0)
                features.append(float(value) if value is not None else 0.0)
        else:
            for feature in self.features:
                if feature in token_data:
                    value = token_data[feature]
                    features.append(float(value) if value is not None else 0.0)
                else:
                    features.append(0.0)
        
        # Convert to numpy array and reshape
        return np.array(features).reshape(1, -1)'''
        
        new_method = '''def prepare_features(self, token_data):
        """
        Prepare features for prediction
        
        :param token_data: Token data dictionary or DataFrame row
        :return: Prepared features as numpy array
        """
        features = []
        
        # Handle both dictionary and DataFrame row input
        if isinstance(token_data, dict):
            for feature in self.features:
                value = token_data.get(feature, 0.0)
                features.append(float(value) if value is not None else 0.0)
        else:
            for feature in self.features:
                if feature in token_data:
                    value = token_data[feature]
                    features.append(float(value) if value is not None else 0.0)
                else:
                    # Try alternative column names
                    if feature == 'mcap' and 'market_cap' in token_data:
                        value = token_data['market_cap']
                    elif feature == 'holders' and 'holder_count' in token_data:
                        value = token_data['holder_count']
                    else:
                        value = 0.0
                    features.append(float(value) if value is not None else 0.0)
        
        # Convert to numpy array and reshape
        return np.array(features).reshape(1, -1)'''
        
        content = content.replace(old_method, new_method)
    
    # Write the updated file
    with open('ml_model.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Updated ml_model.py with correct features")

if __name__ == "__main__":
    fix_ml_model()