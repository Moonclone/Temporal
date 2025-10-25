import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class TechnicalDebtPredictor:
    """Predicts future technical debt using temporal patterns"""
    
    def __init__(self, analysis_file: str = "temporal_analysis.json"):
        self.analysis_file = analysis_file
        self.analysis_data = None
        self.predictions = {}
        
    def load_analysis(self):
        """Load temporal analysis data"""
        print(f"📂 Loading analysis from: {self.analysis_file}")
        
        with open(self.analysis_file, 'r') as f:
            self.analysis_data = json.load(f)
        
        print(f"✅ Loaded data for {len(self.analysis_data['file_evolution'])} files")
    
    def predict_complexity_growth(self, months_ahead: int = 6) -> Dict:
        """
        Predict which files will have growing complexity in the future
        
        Args:
            months_ahead: How many months to predict into the future
            
        Returns:
            Dict with predictions for each file
        """
        print(f"\n🔮 Predicting complexity growth {months_ahead} months ahead...")
        
        predictions = []
        
        for filename, history in self.analysis_data['file_evolution'].items():
            if len(history) < 3:  # Need at least 3 data points
                continue
            
            # Extract complexity over time
            complexities = []
            timestamps = []
            
            for entry in history:
                complexity = entry.get('complexity')
                if complexity is not None and complexity > 0:
                    complexities.append(complexity)
                    # Convert date string to timestamp
                    date_str = entry['date']
                    if isinstance(date_str, str):
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date = date_str
                    timestamps.append(date.timestamp())
            
            if len(complexities) < 3:
                continue
            
            # Train simple linear regression
            X = np.array(timestamps).reshape(-1, 1)
            y = np.array(complexities)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict future
            last_timestamp = timestamps[-1]
            future_timestamp = last_timestamp + (months_ahead * 30 * 24 * 60 * 60)
            
            current_complexity = complexities[-1]
            predicted_complexity = model.predict([[future_timestamp]])[0]
            
            growth_rate = (predicted_complexity - current_complexity) / current_complexity * 100
            
            # Only report significant growth
            if growth_rate > 20:  # 20% growth threshold
                predictions.append({
                    'filename': filename,
                    'current_complexity': int(current_complexity),
                    'predicted_complexity': int(predicted_complexity),
                    'growth_rate': round(growth_rate, 1),
                    'risk_level': self._assess_risk(growth_rate),
                    'months_ahead': months_ahead
                })
        
        # Sort by growth rate
        predictions.sort(key=lambda x: x['growth_rate'], reverse=True)
        
        self.predictions['complexity_growth'] = predictions
        
        self._print_complexity_predictions(predictions[:10], months_ahead)
        
        return predictions
    
    def predict_bug_probability(self) -> List[Dict]:
        """
        Predict which files are likely to have bugs based on patterns
        """
        print("\n🐛 Predicting bug probability...")
        
        bug_predictions = []
        
        for filename, history in self.analysis_data['file_evolution'].items():
            if len(history) < 5:
                continue
            
            # Calculate churn rate (how often file changes)
            total_changes = sum(entry.get('changes', 0) for entry in history)
            avg_change_size = total_changes / len(history) if history else 0
            
            # Files with many small changes often have bugs
            small_changes = sum(1 for entry in history if entry.get('changes', 0) < 10)
            small_change_ratio = small_changes / len(history)
            
            # Calculate complexity volatility
            complexities = [e.get('complexity', 0) for e in history if e.get('complexity')]
            complexity_std = np.std(complexities) if len(complexities) > 1 else 0
            
            # Bug probability score (0-100)
            bug_score = (
                min(len(history) * 5, 40) +  # Frequent changes
                (small_change_ratio * 30) +   # Lots of small fixes
                min(complexity_std * 2, 30)   # Unstable complexity
            )
            
            if bug_score > 50:
                bug_predictions.append({
                    'filename': filename,
                    'bug_probability': round(bug_score, 1),
                    'total_changes': len(history),
                    'small_change_ratio': round(small_change_ratio * 100, 1),
                    'recommendation': self._get_bug_recommendation(bug_score)
                })
        
        bug_predictions.sort(key=lambda x: x['bug_probability'], reverse=True)
        
        self.predictions['bug_probability'] = bug_predictions
        
        self._print_bug_predictions(bug_predictions[:10])
        
        return bug_predictions
    
    def simulate_alternate_timeline(self, filename: str) -> Dict:
        """
        Counterfactual analysis: What if this file was refactored earlier?
        """
        print(f"\n⏱️  Simulating alternate timeline for: {filename}")
        
        if filename not in self.analysis_data['file_evolution']:
            print(f"❌ File not found in analysis")
            return {}
        
        history = self.analysis_data['file_evolution'][filename]
        
        # Current timeline
        current_complexity = [e.get('complexity', 0) for e in history if e.get('complexity', 0) > 0]
        current_total_changes = len(history)
        
        # Simulated timeline: What if refactored at 50% point?
        refactor_point = len(history) // 2
        
        # After refactor, complexity reduces by 40% and future growth slows
        simulated_complexity = current_complexity.copy()
        for i in range(refactor_point, len(simulated_complexity)):
            simulated_complexity[i] = simulated_complexity[i] * 0.7  # 30% reduction
        
        current_final = current_complexity[-1] if current_complexity else 0
        simulated_final = simulated_complexity[-1] if simulated_complexity else 0
        
        improvement = ((current_final - simulated_final) / current_final * 100) if current_final > 0 else 0
        
        result = {
            'filename': filename,
            'current_timeline': {
                'final_complexity': int(current_final),
                'total_changes': current_total_changes
            },
            'refactored_timeline': {
                'final_complexity': int(simulated_final),
                'estimated_changes_saved': int(current_total_changes * 0.2)  # 20% fewer changes
            },
            'improvement': round(improvement, 1),
            'recommendation': f"Refactoring could reduce complexity by {improvement:.0f}%"
        }
        
        print(f"\n📊 Timeline Comparison:")
        print(f"   Current: Complexity = {int(current_final)}, Changes = {current_total_changes}")
        print(f"   If Refactored: Complexity = {int(simulated_final)}, Est. Changes = {current_total_changes - int(current_total_changes * 0.2)}")
        print(f"   💡 Improvement: {improvement:.1f}%")
        
        return result
    
    def _assess_risk(self, growth_rate: float) -> str:
        """Assess risk level based on growth rate"""
        if growth_rate > 100:
            return "🔴 CRITICAL"
        elif growth_rate > 50:
            return "🟠 HIGH"
        elif growth_rate > 20:
            return "🟡 MEDIUM"
        else:
            return "🟢 LOW"
    
    def _get_bug_recommendation(self, bug_score: float) -> str:
        """Get recommendation based on bug probability"""
        if bug_score > 70:
            return "URGENT: Schedule immediate code review and refactoring"
        elif bug_score > 60:
            return "HIGH PRIORITY: Add comprehensive tests and monitoring"
        else:
            return "MODERATE: Increase test coverage"
    
    def _print_complexity_predictions(self, predictions: List[Dict], months: int):
        """Print complexity growth predictions"""
        
        if not predictions:
            print("✅ No significant complexity growth predicted")
            return
        
        print("\n" + "="*80)
        print(f"🔮 COMPLEXITY GROWTH PREDICTIONS ({months} months ahead)")
        print("="*80)
        
        for idx, pred in enumerate(predictions, 1):
            print(f"\n[{idx}] {pred['filename']}")
            print(f"    Current: {pred['current_complexity']}")
            print(f"    Predicted: {pred['predicted_complexity']}")
            print(f"    Growth: {pred['growth_rate']}%")
            print(f"    Risk: {pred['risk_level']}")
        
        print("\n" + "="*80)
    
    def _print_bug_predictions(self, predictions: List[Dict]):
        """Print bug probability predictions"""
        
        if not predictions:
            print("✅ No high-risk files for bugs detected")
            return
        
        print("\n" + "="*80)
        print("🐛 BUG PROBABILITY PREDICTIONS")
        print("="*80)
        
        for idx, pred in enumerate(predictions, 1):
            print(f"\n[{idx}] {pred['filename']}")
            print(f"    Bug Probability: {pred['bug_probability']}%")
            print(f"    Total Changes: {pred['total_changes']}")
            print(f"    Small Fix Ratio: {pred['small_change_ratio']}%")
            print(f"    💡 {pred['recommendation']}")
        
        print("\n" + "="*80)
    
    def generate_report(self, output_file: str = "prediction_report.json"):
        """Generate comprehensive prediction report"""
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'predictions': self.predictions,
            'summary': {
                'files_with_predicted_growth': len(self.predictions.get('complexity_growth', [])),
                'high_bug_risk_files': len([p for p in self.predictions.get('bug_probability', []) if p['bug_probability'] > 60])
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Prediction report saved to: {output_file}")


def main():
    """Test the prediction engine"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║         🔮 TECHNICAL DEBT PREDICTION ENGINE v1.0              ║
    ║              Forecasting Your Codebase Future                 ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    predictor = TechnicalDebtPredictor("temporal_analysis.json")
    predictor.load_analysis()
    
    # Predict complexity growth
    complexity_predictions = predictor.predict_complexity_growth(months_ahead=6)
    
    # Predict bug probability
    bug_predictions = predictor.predict_bug_probability()
    
    # Simulate alternate timeline for top risky file
    if complexity_predictions:
        top_risky_file = complexity_predictions[0]['filename']
        predictor.simulate_alternate_timeline(top_risky_file)
    
    # Generate report
    predictor.generate_report()
    
    print("\n✅ Prediction complete!")
    print("🚀 CHRONOS can now see into the future of your codebase!")


if __name__ == "__main__":
    main()