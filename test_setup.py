import sys

def test_imports():
    """Test all required imports"""
    tests = []
    
    # Test CrewAI
    try:
        from crewai import Agent, Task, Crew
        tests.append(("✅ CrewAI", True))
    except Exception as e:
        tests.append(("❌ CrewAI", False, str(e)))
    
    # Test LangChain
    try:
        from langchain_community.llms import Ollama
        tests.append(("✅ LangChain", True))
    except Exception as e:
        tests.append(("❌ LangChain", False, str(e)))
    
    # Test Kubernetes
    try:
        from kubernetes import client, config
        tests.append(("✅ Kubernetes Client", True))
    except Exception as e:
        tests.append(("❌ Kubernetes Client", False, str(e)))
    
    # Test Data Science
    try:
        import numpy as np
        import pandas as pd
        import networkx as nx
        tests.append(("✅ Data Science Stack", True))
    except Exception as e:
        tests.append(("❌ Data Science Stack", False, str(e)))
    
    # Test FastAPI
    try:
        from fastapi import FastAPI
        tests.append(("✅ FastAPI", True))
    except Exception as e:
        tests.append(("❌ FastAPI", False, str(e)))
    
    # Print results
    print("\n" + "="*50)
    print("CHRONOS SETUP VALIDATION")
    print("="*50 + "\n")
    
    for test in tests:
        if len(test) == 2:
            print(f"{test[0]}")
        else:
            print(f"{test[0]}: {test[2]}")
    
    print("\n" + "="*50)
    
    # Check if all passed
    failed = [t for t in tests if not t[1]]
    if failed:
        print(f"\n❌ {len(failed)} tests failed")
        return False
    else:
        print("\n✅ All tests passed! Ready to build CHRONOS!")
        return True

def test_ollama():
    """Test Ollama connection"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("\n✅ Ollama is running")
            models = response.json().get('models', [])
            print(f"   Available models: {len(models)}")
            for model in models:
                print(f"   - {model['name']}")
            return True
        else:
            print("\n❌ Ollama not responding")
            return False
    except Exception as e:
        print(f"\n❌ Ollama connection failed: {e}")
        print("   Run: ollama serve")
        return False

def test_kubernetes():
    """Test Kubernetes connection"""
    try:
        from kubernetes import client, config
        config.load_kube_config()
        v1 = client.CoreV1Api()
        nodes = v1.list_node()
        print(f"\n✅ Kubernetes connected")
        print(f"   Nodes: {len(nodes.items)}")
        for node in nodes.items:
            print(f"   - {node.metadata.name}")
        return True
    except Exception as e:
        print(f"\n❌ Kubernetes connection failed: {e}")
        print("   Make sure cluster is running: kubectl get nodes")
        return False

if __name__ == "__main__":
    print("\n🚀 Testing CHRONOS Setup...\n")
    
    imports_ok = test_imports()
    ollama_ok = test_ollama()
    k8s_ok = test_kubernetes()
    
    if imports_ok and ollama_ok and k8s_ok:
        print("\n" + "="*50)
        print("🎉 SETUP COMPLETE! Ready for Step 2")
        print("="*50 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*50)
        print("⚠️  Some components need attention")
        print("="*50 + "\n")
        sys.exit(1)