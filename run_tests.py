#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试运行脚本
用于运行项目的所有测试，包括单元测试和集成测试
"""

import os
import sys
import unittest
import argparse
import logging
from typing import List, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_runner')


def discover_tests(test_dir: str, pattern: str = 'test_*.py') -> unittest.TestSuite:
    """
    发现测试用例
    
    Args:
        test_dir: 测试目录
        pattern: 测试文件匹配模式
        
    Returns:
        测试套件
    """
    logger.info(f"从目录 {test_dir} 中发现测试用例，匹配模式: {pattern}")
    return unittest.defaultTestLoader.discover(test_dir, pattern=pattern)


def run_tests(test_suite: unittest.TestSuite, verbosity: int = 2) -> unittest.TestResult:
    """
    运行测试套件
    
    Args:
        test_suite: 测试套件
        verbosity: 详细程度
        
    Returns:
        测试结果
    """
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(test_suite)


def run_specific_tests(test_names: List[str], verbosity: int = 2) -> unittest.TestResult:
    """
    运行指定的测试
    
    Args:
        test_names: 测试名称列表
        verbosity: 详细程度
        
    Returns:
        测试结果
    """
    suite = unittest.TestSuite()
    
    for test_name in test_names:
        try:
            # 尝试加载测试模块
            if test_name.endswith('.py'):
                test_name = test_name[:-3]
            
            # 将路径分隔符替换为点
            test_name = test_name.replace('/', '.').replace('\\', '.')
            
            # 如果以tests.开头，则去掉
            if test_name.startswith('tests.'):
                test_name = test_name[6:]
            
            # 添加tests.前缀
            if not test_name.startswith('tests.'):
                test_name = f'tests.{test_name}'
                
            logger.info(f"加载测试模块: {test_name}")
            tests = unittest.defaultTestLoader.loadTestsFromName(test_name)
            suite.addTest(tests)
        except (ImportError, AttributeError) as e:
            logger.error(f"加载测试 {test_name} 失败: {e}")
    
    return run_tests(suite, verbosity)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='测试运行脚本')
    parser.add_argument('--test', '-t', nargs='*', help='要运行的特定测试，例如 test_spider 或 test_integration')
    parser.add_argument('--pattern', '-p', default='test_*.py', help='测试文件匹配模式')
    parser.add_argument('--verbosity', '-v', type=int, default=2, help='输出详细程度')
    parser.add_argument('--unit', '-u', action='store_true', help='只运行单元测试')
    parser.add_argument('--integration', '-i', action='store_true', help='只运行集成测试')
    parser.add_argument('--full', '-f', action='store_true', help='运行全面集成测试')
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 添加项目根目录到系统路径
    project_root = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, project_root)
    
    # 测试目录
    test_dir = os.path.join(project_root, 'tests')
    
    # 运行特定测试
    if args.test:
        logger.info(f"运行特定测试: {args.test}")
        result = run_specific_tests(args.test, args.verbosity)
    # 只运行单元测试
    elif args.unit:
        logger.info("只运行单元测试")
        # 排除集成测试
        pattern = 'test_[!i]*.py'  # 排除以i开头的测试文件
        suite = discover_tests(test_dir, pattern)
        result = run_tests(suite, args.verbosity)
    # 只运行集成测试
    elif args.integration:
        logger.info("只运行集成测试")
        # 只包含集成测试
        pattern = 'test_i*.py'  # 只包含以i开头的测试文件
        suite = discover_tests(test_dir, pattern)
        result = run_tests(suite, args.verbosity)
    # 运行全面集成测试
    elif args.full:
        logger.info("运行全面集成测试")
        # 只包含全面集成测试
        pattern = 'test_full*.py'
        suite = discover_tests(test_dir, pattern)
        result = run_tests(suite, args.verbosity)
    # 运行所有测试
    else:
        logger.info("运行所有测试")
        suite = discover_tests(test_dir, args.pattern)
        result = run_tests(suite, args.verbosity)
    
    # 输出测试结果摘要
    logger.info(f"测试完成: 运行 {result.testsRun} 个测试")
    logger.info(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    logger.info(f"失败: {len(result.failures)}")
    logger.info(f"错误: {len(result.errors)}")
    
    # 如果有失败或错误，则返回非零退出码
    if result.failures or result.errors:
        sys.exit(1)


if __name__ == '__main__':
    main() 