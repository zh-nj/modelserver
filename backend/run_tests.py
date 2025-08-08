#!/usr/bin/env python3
"""
测试运行器
提供不同类型的测试运行选项
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd: list, description: str) -> int:
    """运行命令并返回退出码"""
    print(f"\n{'='*60}")
    print(f"运行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def run_unit_tests(verbose: bool = False, coverage: bool = True) -> int:
    """运行单元测试"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
    
    cmd.extend([
        "-m", "unit",
        "tests/"
    ])
    
    return run_command(cmd, "单元测试")


def run_integration_tests(verbose: bool = False) -> int:
    """运行集成测试"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "-m", "integration",
        "tests/"
    ])
    
    return run_command(cmd, "集成测试")


def run_all_tests(verbose: bool = False, coverage: bool = True) -> int:
    """运行所有测试"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=app",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--cov-fail-under=80"
        ])
    
    cmd.append("tests/")
    
    return run_command(cmd, "所有测试")


def run_specific_test(test_path: str, verbose: bool = False) -> int:
    """运行特定测试"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.append(test_path)
    
    return run_command(cmd, f"特定测试: {test_path}")


def run_parallel_tests(workers: int = 4, verbose: bool = False) -> int:
    """并行运行测试"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "-n", str(workers),
        "--cov=app",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing",
        "tests/"
    ])
    
    return run_command(cmd, f"并行测试 (workers={workers})")


def run_performance_tests(verbose: bool = False) -> int:
    """运行性能测试"""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend([
        "-m", "slow",
        "--benchmark-only",
        "tests/"
    ])
    
    return run_command(cmd, "性能测试")


def check_code_quality() -> int:
    """检查代码质量"""
    print("\n" + "="*60)
    print("代码质量检查")
    print("="*60)
    
    # 运行 black 格式检查
    print("\n检查代码格式 (black)...")
    result = subprocess.run(["black", "--check", "--diff", "app/", "tests/"])
    if result.returncode != 0:
        print("❌ 代码格式检查失败")
        return result.returncode
    
    # 运行 isort 导入排序检查
    print("\n检查导入排序 (isort)...")
    result = subprocess.run(["isort", "--check-only", "--diff", "app/", "tests/"])
    if result.returncode != 0:
        print("❌ 导入排序检查失败")
        return result.returncode
    
    # 运行 flake8 代码风格检查
    print("\n检查代码风格 (flake8)...")
    result = subprocess.run(["flake8", "app/", "tests/"])
    if result.returncode != 0:
        print("❌ 代码风格检查失败")
        return result.returncode
    
    # 运行 mypy 类型检查
    print("\n检查类型注解 (mypy)...")
    result = subprocess.run(["mypy", "app/"])
    if result.returncode != 0:
        print("❌ 类型检查失败")
        return result.returncode
    
    print("\n✅ 所有代码质量检查通过")
    return 0


def generate_coverage_report() -> int:
    """生成覆盖率报告"""
    cmd = ["python", "-m", "pytest", 
           "--cov=app", 
           "--cov-report=html:htmlcov",
           "--cov-report=term-missing",
           "--cov-report=xml",
           "tests/"]
    
    result = run_command(cmd, "生成覆盖率报告")
    
    if result == 0:
        print(f"\n✅ 覆盖率报告已生成:")
        print(f"   HTML报告: htmlcov/index.html")
        print(f"   XML报告: coverage.xml")
    
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LLM推理服务测试运行器")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--no-coverage", action="store_true", help="禁用覆盖率报告")
    parser.add_argument("--parallel", "-p", type=int, metavar="N", help="并行运行测试，指定worker数量")
    
    subparsers = parser.add_subparsers(dest="command", help="测试命令")
    
    # 单元测试
    unit_parser = subparsers.add_parser("unit", help="运行单元测试")
    
    # 集成测试
    integration_parser = subparsers.add_parser("integration", help="运行集成测试")
    
    # 所有测试
    all_parser = subparsers.add_parser("all", help="运行所有测试")
    
    # 特定测试
    specific_parser = subparsers.add_parser("test", help="运行特定测试")
    specific_parser.add_argument("path", help="测试文件或目录路径")
    
    # 性能测试
    perf_parser = subparsers.add_parser("perf", help="运行性能测试")
    
    # 代码质量检查
    quality_parser = subparsers.add_parser("quality", help="代码质量检查")
    
    # 覆盖率报告
    coverage_parser = subparsers.add_parser("coverage", help="生成覆盖率报告")
    
    args = parser.parse_args()
    
    # 如果没有指定命令，默认运行所有测试
    if not args.command:
        args.command = "all"
    
    coverage = not args.no_coverage
    
    try:
        if args.parallel and args.command in ["unit", "all"]:
            return run_parallel_tests(args.parallel, args.verbose)
        elif args.command == "unit":
            return run_unit_tests(args.verbose, coverage)
        elif args.command == "integration":
            return run_integration_tests(args.verbose)
        elif args.command == "all":
            return run_all_tests(args.verbose, coverage)
        elif args.command == "test":
            return run_specific_test(args.path, args.verbose)
        elif args.command == "perf":
            return run_performance_tests(args.verbose)
        elif args.command == "quality":
            return check_code_quality()
        elif args.command == "coverage":
            return generate_coverage_report()
        else:
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        print("\n\n❌ 测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n\n❌ 测试运行出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())