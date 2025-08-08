#!/usr/bin/env python3
"""
测试前端功能是否正常工作
"""
import requests
import time
import json

def test_backend_health():
    """测试后端健康状态"""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        print(f"后端健康检查: {response.status_code}")
        if response.status_code == 200:
            print(f"响应内容: {response.json()}")
            return True
    except Exception as e:
        print(f"后端健康检查失败: {e}")
    return False

def test_frontend_access():
    """测试前端页面访问"""
    try:
        response = requests.get('http://localhost:3000/', timeout=5)
        print(f"前端页面访问: {response.status_code}")
        if response.status_code == 200:
            print("前端页面可以正常访问")
            return True
    except Exception as e:
        print(f"前端页面访问失败: {e}")
    return False

def test_api_endpoints():
    """测试API端点"""
    endpoints = [
        '/api/system/metrics',
        '/api/models',
        '/api/system/gpu-info',
        '/docs'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f'http://localhost:8000{endpoint}', timeout=5)
            print(f"API {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"API {endpoint} 失败: {e}")

if __name__ == '__main__':
    print("=== LLM推理服务前端功能测试 ===")
    
    print("\n1. 测试后端服务...")
    backend_ok = test_backend_health()
    
    print("\n2. 测试前端访问...")
    frontend_ok = test_frontend_access()
    
    print("\n3. 测试API端点...")
    test_api_endpoints()
    
    print("\n=== 测试总结 ===")
    print(f"后端服务: {'✅ 正常' if backend_ok else '❌ 异常'}")
    print(f"前端访问: {'✅ 正常' if frontend_ok else '❌ 异常'}")
    
    if backend_ok and frontend_ok:
        print("\n🎉 前端功能测试通过！")
        print("可以通过以下地址访问:")
        print("- 前端界面: http://localhost:3000")
        print("- API文档: http://localhost:8000/docs")
        print("- 后端健康检查: http://localhost:8000/health")
    else:
        print("\n⚠️  存在问题，请检查服务状态")