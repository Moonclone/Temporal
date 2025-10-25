import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from pydriller import Repository
import git
from collections import defaultdict
import json


class CodeArchaeologist:
    """Mines Git repositories to build temporal understanding of code evolution"""
    
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.repo = None
        self.commits_data = []
        self.file_evolution = defaultdict(list)
        
    def clone_or_open_repo(self, git_url: str = None):
        """Clone repository or open existing one"""
        
        if git_url:
            print(f"📥 Cloning repository: {git_url}")
            try:
                self.repo = git.Repo.clone_from(git_url, self.repo_path)
                print(f"✅ Cloned to: {self.repo_path}")
            except git.exc.GitCommandError as e:
                if "already exists" in str(e):
                    print(f"📂 Repository already exists, opening...")
                    self.repo = git.Repo(self.repo_path)
                else:
                    raise
        else:
            print(f"📂 Opening repository: {self.repo_path}")
            self.repo = git.Repo(self.repo_path)
    
    def analyze_history(self, months_back: int = 12, max_commits: int = 500):
        """
        Analyze Git history to extract temporal patterns
        
        Args:
            months_back: How many months of history to analyze
            max_commits: Maximum number of commits to process
        """
        print(f"\n🔍 Analyzing Git history...")
        print(f"   Looking back: {months_back} months")
        print(f"   Max commits: {max_commits}")
        
        since = datetime.now() - timedelta(days=months_back * 30)
        
        commit_count = 0
        
        for commit in Repository(self.repo_path, since=since).traverse_commits():
            if commit_count >= max_commits:
                break
            
            commit_data = {
                'hash': commit.hash[:8],
                'author': commit.author.name,
                'date': commit.committer_date,
                'message': commit.msg.split('\n')[0][:100],  # First line only
                'files_changed': len(commit.modified_files),
                'insertions': commit.insertions,
                'deletions': commit.deletions,
                'modified_files': []
            }
            
            # Analyze each modified file
            for modified_file in commit.modified_files:
                if not modified_file.filename:
                    continue
                
                file_data = {
                    'filename': modified_file.filename,
                    'added_lines': modified_file.added_lines,
                    'deleted_lines': modified_file.deleted_lines,
                    'complexity': modified_file.complexity if hasattr(modified_file, 'complexity') else 0,
                    'nloc': modified_file.nloc if hasattr(modified_file, 'nloc') else 0
                }
                
                commit_data['modified_files'].append(file_data)
                
                # Track file evolution over time
                self.file_evolution[modified_file.filename].append({
                    'date': commit.committer_date,
                    'hash': commit.hash[:8],
                    'author': commit.author.name,
                    'complexity': file_data['complexity'],
                    'nloc': file_data['nloc'],
                    'changes': file_data['added_lines'] + file_data['deleted_lines']
                })
            
            self.commits_data.append(commit_data)
            commit_count += 1
            
            if commit_count % 50 == 0:
                print(f"   Processed {commit_count} commits...")
        
        print(f"✅ Analyzed {commit_count} commits")
        print(f"📁 Tracked {len(self.file_evolution)} unique files\n")
        
        return self.commits_data
    
    def identify_hotspots(self, top_n: int = 10) -> List[Dict]:
        """
        Identify files that change frequently (potential problem areas)
        """
        print("🔥 Identifying code hotspots...")
        
        file_change_counts = {}
        file_complexity_trends = {}
        
        for filename, history in self.file_evolution.items():
            file_change_counts[filename] = len(history)
            
            # Calculate complexity trend (growing = problem)
            if len(history) >= 2:
                complexities = [h.get('complexity', 0) for h in history if h.get('complexity')]
                if complexities:
                    # Simple trend: compare first half vs second half
                    mid = len(complexities) // 2
                    first_half_avg = sum(complexities[:mid]) / mid if mid > 0 else 0
                    second_half_avg = sum(complexities[mid:]) / (len(complexities) - mid) if len(complexities) > mid else 0
                    
                    trend = second_half_avg - first_half_avg
                    file_complexity_trends[filename] = trend
        
        # Sort by change frequency
        hotspots = sorted(file_change_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        results = []
        for filename, change_count in hotspots:
            complexity_trend = file_complexity_trends.get(filename, 0)
            
            results.append({
                'filename': filename,
                'change_count': change_count,
                'complexity_trend': complexity_trend,
                'risk_score': change_count * (1 + max(0, complexity_trend) * 0.1),
                'status': '🔴 HIGH RISK' if complexity_trend > 10 else '🟡 MODERATE' if complexity_trend > 0 else '🟢 STABLE'
            })
        
        # Print report
        print("\n" + "="*80)
        print("🔥 CODE HOTSPOTS (Frequently Changed Files)")
        print("="*80)
        
        for idx, hotspot in enumerate(results, 1):
            print(f"\n[{idx}] {hotspot['filename']}")
            print(f"    Changes: {hotspot['change_count']}")
            print(f"    Complexity Trend: {hotspot['complexity_trend']:+.1f}")
            print(f"    Risk Score: {hotspot['risk_score']:.1f}")
            print(f"    Status: {hotspot['status']}")
        
        print("\n" + "="*80 + "\n")
        
        return results
    
    def detect_decay_patterns(self) -> Dict:
        """
        Detect patterns of code decay (increasing complexity, decreasing quality)
        """
        print("📉 Detecting code decay patterns...")
        
        patterns = {
            'files_with_growing_complexity': [],
            'files_with_frequent_fixes': [],
            'abandoned_files': [],
            'summary': {}
        }
        
        for filename, history in self.file_evolution.items():
            if len(history) < 3:
                continue
            
            # Pattern 1: Growing complexity
            complexities = [h.get('complexity', 0) for h in history if h.get('complexity')]
            if len(complexities) >= 3:
                if complexities[-1] > complexities[0] * 1.5:  # 50% increase
                    patterns['files_with_growing_complexity'].append({
                        'filename': filename,
                        'initial_complexity': complexities[0],
                        'current_complexity': complexities[-1],
                        'growth_rate': (complexities[-1] - complexities[0]) / complexities[0] * 100
                    })
            
            # Pattern 2: Frequent fixes (lots of small changes)
            small_changes = [h for h in history if h.get('changes', 0) < 10]
            if len(small_changes) > len(history) * 0.7:  # 70% are small fixes
                patterns['files_with_frequent_fixes'].append({
                    'filename': filename,
                    'total_changes': len(history),
                    'small_fixes': len(small_changes),
                    'fix_ratio': len(small_changes) / len(history)
                })
            
            # Pattern 3: Abandoned files (no recent changes)
            last_change = history[-1]['date']
            days_since = (datetime.now(last_change.tzinfo) - last_change).days
            if days_since > 180:  # 6 months
                patterns['abandoned_files'].append({
                    'filename': filename,
                    'days_since_last_change': days_since,
                    'last_author': history[-1]['author']
                })
        
        patterns['summary'] = {
            'total_files_analyzed': len(self.file_evolution),
            'files_with_decay': len(patterns['files_with_growing_complexity']),
            'files_needing_refactor': len(patterns['files_with_frequent_fixes']),
            'potentially_abandoned': len(patterns['abandoned_files'])
        }
        
        self._print_decay_report(patterns)
        
        return patterns
    
    def _print_decay_report(self, patterns: Dict):
        """Print decay analysis report"""
        
        summary = patterns['summary']
        
        print("\n" + "="*80)
        print("📉 CODE DECAY ANALYSIS")
        print("="*80)
        print(f"Total files analyzed: {summary['total_files_analyzed']}")
        print(f"Files showing complexity growth: {summary['files_with_decay']}")
        print(f"Files needing refactor: {summary['files_needing_refactor']}")
        print(f"Potentially abandoned: {summary['potentially_abandoned']}")
        
        if patterns['files_with_growing_complexity']:
            print("\n🔴 TOP FILES WITH GROWING COMPLEXITY:")
            for file in patterns['files_with_growing_complexity'][:5]:
                print(f"   • {file['filename']}")
                print(f"     Growth: {file['growth_rate']:.1f}% (from {file['initial_complexity']} → {file['current_complexity']})")
        
        if patterns['files_with_frequent_fixes']:
            print("\n🟡 FILES WITH FREQUENT SMALL FIXES (Possible Quality Issues):")
            for file in patterns['files_with_frequent_fixes'][:5]:
                print(f"   • {file['filename']}")
                print(f"     Fix ratio: {file['fix_ratio']*100:.1f}% ({file['small_fixes']}/{file['total_changes']} changes)")
        
        print("\n" + "="*80 + "\n")
    
    def export_data(self, output_file: str = "temporal_analysis.json"):
        """Export analysis data for machine learning"""
        
        export_data = {
            'commits': self.commits_data,
            'file_evolution': {k: v for k, v in self.file_evolution.items()},
            'analysis_date': datetime.now().isoformat()
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"💾 Exported temporal data to: {output_file}")


def main():
    """Test the code archaeologist"""
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              🔮 CODE ARCHAEOLOGIST v1.0                       ║
    ║           Mining Git History for Predictions                  ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Test with a sample repository
    # Option 1: Clone a public repo
    test_repo_url = "https://github.com/kubernetes/kubernetes"
    test_repo_path = "./data/kubernetes"
    
    # Option 2: Use local repo (uncomment and modify)
    # test_repo_path = "path/to/your/local/repo"
    # test_repo_url = None
    
    archaeologist = CodeArchaeologist(test_repo_path)
    
    # For demo, let's use a smaller repo
    print("📥 For this demo, we'll analyze the CHRONOS repo itself!")
    test_repo_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    archaeologist = CodeArchaeologist(test_repo_path)
    archaeologist.clone_or_open_repo()
    
    # Analyze history
    commits = archaeologist.analyze_history(months_back=6, max_commits=100)
    
    # Find hotspots
    hotspots = archaeologist.identify_hotspots(top_n=10)
    
    # Detect decay
    decay_patterns = archaeologist.detect_decay_patterns()
    
    # Export for ML
    archaeologist.export_data()
    
    print("\n✅ Temporal analysis complete!")
    print("📊 Ready for prediction engine in next step!")


if __name__ == "__main__":
    main()