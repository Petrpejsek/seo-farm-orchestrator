#!/usr/bin/env python3
"""
🔍 DEBUG TEST RUNNER
====================

Nástroj pro spouštění debugging testů:
- Jednotlivé testy komponent
- Kompletní test suite
- Výsledky v přehledném formátu
- Automatické reporty
"""

import os
import sys
import time
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Temporal imports
from temporalio.client import Client
from temporalio.common import RetryPolicy

# Import našich nástrojů
sys.path.append(os.path.dirname(__file__))
from helpers.db_logger import db_logger
from helpers.db_connection_audit import run_connection_audit, get_connection_stats
from helpers.db_activity_monitor import start_database_monitoring, stop_database_monitoring, get_database_health_report
from workflows.debug_simple_workflows import create_comprehensive_test_suite
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class TestResult:
    """Výsledek jednotlivého testu"""
    test_name: str
    workflow_type: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error: Optional[str] = None


class DebugTestRunner:
    """Hlavní třída pro spouštění debugging testů"""
    
    def __init__(self, temporal_host: str = "localhost:7233"):
        self.temporal_host = temporal_host
        self.client = None
        self.test_results = []
        
    async def initialize(self):
        """Inicializuje Temporal client"""
        try:
            self.client = await Client.connect(self.temporal_host)
            logger.info(f"✅ Connected to Temporal: {self.temporal_host}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Temporal: {e}")
            raise
    
    async def run_single_test(self, workflow_name: str, config: Dict[str, Any], timeout_minutes: int = 10) -> TestResult:
        """Spustí jeden test workflow"""
        test_start = time.time()
        workflow_id = f"debug_test_{workflow_name}_{int(test_start)}"
        
        logger.info(f"🧪 STARTING_TEST: {workflow_name} ({workflow_id})")
        
        try:
            # Spuštění workflow podle typu
            if workflow_name == "DatabaseTestWorkflow":
                from workflows.debug_simple_workflows import DatabaseTestWorkflow
                result = await self.client.execute_workflow(
                    DatabaseTestWorkflow.run,
                    config,
                    id=workflow_id,
                    task_queue="default",
                    execution_timeout=timedelta(minutes=timeout_minutes)
                )
            
            elif workflow_name == "SingleAssistantTestWorkflow":
                from workflows.debug_simple_workflows import SingleAssistantTestWorkflow
                result = await self.client.execute_workflow(
                    SingleAssistantTestWorkflow.run,
                    config.get("assistant_config", {}),
                    config.get("test_input", "Test input"),
                    id=workflow_id,
                    task_queue="default",
                    execution_timeout=timedelta(minutes=timeout_minutes)
                )
            
            elif workflow_name == "ImageGenerationTestWorkflow":
                from workflows.debug_simple_workflows import ImageGenerationTestWorkflow
                result = await self.client.execute_workflow(
                    ImageGenerationTestWorkflow.run,
                    config.get("test_prompts", []),
                    id=workflow_id,
                    task_queue="default",
                    execution_timeout=timedelta(minutes=timeout_minutes)
                )
            
            elif workflow_name == "PublishScriptTestWorkflow":
                from workflows.debug_simple_workflows import PublishScriptTestWorkflow
                result = await self.client.execute_workflow(
                    PublishScriptTestWorkflow.run,
                    config.get("mock_pipeline_data"),
                    id=workflow_id,
                    task_queue="default",
                    execution_timeout=timedelta(minutes=timeout_minutes)
                )
            
            elif workflow_name == "ConnectionTestWorkflow":
                from workflows.debug_simple_workflows import ConnectionTestWorkflow
                result = await self.client.execute_workflow(
                    ConnectionTestWorkflow.run,
                    config,
                    id=workflow_id,
                    task_queue="default",
                    execution_timeout=timedelta(minutes=timeout_minutes)
                )
            
            else:
                raise ValueError(f"Unknown workflow: {workflow_name}")
            
            duration = time.time() - test_start
            success = result.get("success", False)
            
            test_result = TestResult(
                test_name=workflow_name,
                workflow_type=workflow_name,
                success=success,
                duration=duration,
                details=result
            )
            
            status = "✅" if success else "❌"
            logger.info(f"{status} TEST_COMPLETED: {workflow_name} ({duration:.2f}s)")
            
            return test_result
            
        except Exception as e:
            duration = time.time() - test_start
            error_msg = str(e)
            
            test_result = TestResult(
                test_name=workflow_name,
                workflow_type=workflow_name,
                success=False,
                duration=duration,
                details={},
                error=error_msg
            )
            
            logger.error(f"❌ TEST_FAILED: {workflow_name} ({duration:.2f}s) - {error_msg}")
            
            return test_result
    
    async def run_test_suite(self, test_configs: List[Dict[str, Any]] = None) -> List[TestResult]:
        """Spustí kompletní sadu testů"""
        if not test_configs:
            test_configs = create_comprehensive_test_suite()
        
        logger.info(f"🚀 STARTING_TEST_SUITE: {len(test_configs)} tests")
        
        # Spustit database monitoring
        start_database_monitoring()
        
        results = []
        
        try:
            for i, test_config in enumerate(test_configs):
                workflow_name = test_config["workflow"]
                config = test_config.get("config", {})
                description = test_config.get("description", "")
                
                logger.info(f"🧪 Test {i+1}/{len(test_configs)}: {description}")
                
                result = await self.run_single_test(workflow_name, config)
                results.append(result)
                self.test_results.append(result)
                
                # Krátká pauza mezi testy
                await asyncio.sleep(1)
        
        finally:
            # Zastavit monitoring
            stop_database_monitoring()
        
        # Generování reportu
        successful_tests = sum(1 for r in results if r.success)
        logger.info(f"📊 TEST_SUITE_COMPLETED: {successful_tests}/{len(results)} tests passed")
        
        return results
    
    def generate_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generuje detailní report testů"""
        successful_tests = [r for r in results if r.success]
        failed_tests = [r for r in results if not r.success]
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(results),
                "successful_tests": len(successful_tests),
                "failed_tests": len(failed_tests),
                "success_rate": len(successful_tests) / len(results) if results else 0,
                "total_duration": sum(r.duration for r in results)
            },
            "test_results": [],
            "failed_tests_details": [],
            "recommendations": []
        }
        
        # Detaily jednotlivých testů
        for result in results:
            test_detail = {
                "test_name": result.test_name,
                "success": result.success,
                "duration": result.duration,
                "workflow_type": result.workflow_type
            }
            
            if result.success:
                # Přidat relevantní metriky z úspěšných testů
                if "db_tests" in result.details:
                    test_detail["db_success_rate"] = result.details["db_tests"].get("summary", {}).get("success_rate", 0)
                if "successful_tests" in result.details:
                    test_detail["component_success_rate"] = result.details.get("success_rate", 0)
            
            report["test_results"].append(test_detail)
        
        # Detaily neúspěšných testů
        for result in failed_tests:
            failed_detail = {
                "test_name": result.test_name,
                "error": result.error,
                "duration": result.duration,
                "details": result.details
            }
            report["failed_tests_details"].append(failed_detail)
        
        # Doporučení na základě výsledků
        if len(failed_tests) > len(successful_tests) / 2:
            report["recommendations"].append("High failure rate - check database connectivity and worker configuration")
        
        if any("database" in r.test_name.lower() for r in failed_tests):
            report["recommendations"].append("Database tests failed - run connection audit and check DB health")
        
        if any("image" in r.test_name.lower() for r in failed_tests):
            report["recommendations"].append("Image generation tests failed - check FAL.AI API key and model configuration")
        
        if any("publish" in r.test_name.lower() for r in failed_tests):
            report["recommendations"].append("Publish script tests failed - check publish activity and data transformation")
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: str = None):
        """Uloží report do souboru"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"debug_test_report_{timestamp}.json"
        
        os.makedirs("debug_reports", exist_ok=True)
        filepath = os.path.join("debug_reports", filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📄 Report saved: {filepath}")
        return filepath


async def run_quick_database_check():
    """Rychlá kontrola databáze bez Temporal workflow"""
    logger.info("🔍 QUICK_DATABASE_CHECK_START")
    
    try:
        # Connection audit
        audit_result = run_connection_audit()
        
        # Connection stats
        conn_stats = get_connection_stats()
        
        # Health report
        health_report = get_database_health_report()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "connection_audit": audit_result,
            "connection_stats": conn_stats,
            "health_report": health_report,
            "overall_health": "HEALTHY" if audit_result.get("success", False) else "WARNING"
        }
        
        logger.info(f"✅ QUICK_DATABASE_CHECK_COMPLETED: {report['overall_health']}")
        return report
        
    except Exception as e:
        logger.error(f"❌ QUICK_DATABASE_CHECK_FAILED: {e}")
        return {"error": str(e), "overall_health": "ERROR"}


async def main():
    """Hlavní funkce pro spuštění testů"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug Test Runner")
    parser.add_argument("--test", choices=["all", "database", "image", "publish", "connection", "quick"], 
                       default="quick", help="Type of test to run")
    parser.add_argument("--temporal-host", default="localhost:7233", help="Temporal server host")
    parser.add_argument("--output", help="Output file for report")
    
    args = parser.parse_args()
    
    if args.test == "quick":
        # Rychlá kontrola bez Temporal
        report = await run_quick_database_check()
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"Report saved to: {args.output}")
        else:
            print(json.dumps(report, indent=2, default=str))
        
        return
    
    # Plné testy s Temporal
    runner = DebugTestRunner(args.temporal_host)
    
    try:
        await runner.initialize()
        
        if args.test == "all":
            results = await runner.run_test_suite()
        else:
            # Jednotlivé testy
            test_configs = create_comprehensive_test_suite()
            filtered_configs = [
                config for config in test_configs 
                if args.test.lower() in config["workflow"].lower()
            ]
            
            if not filtered_configs:
                print(f"No tests found for type: {args.test}")
                return
            
            results = []
            for config in filtered_configs:
                result = await runner.run_single_test(config["workflow"], config.get("config", {}))
                results.append(result)
        
        # Generování reportu
        report = runner.generate_report(results)
        
        if args.output:
            runner.save_report(report, args.output)
        else:
            print(json.dumps(report, indent=2, default=str))
        
        # Výstup do konzole
        print(f"\n📊 Test Summary:")
        print(f"✅ Successful: {report['summary']['successful_tests']}")
        print(f"❌ Failed: {report['summary']['failed_tests']}")
        print(f"📈 Success Rate: {report['summary']['success_rate']:.2%}")
        print(f"⏱️ Total Duration: {report['summary']['total_duration']:.2f}s")
        
        if report['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
    
    except Exception as e:
        logger.error(f"❌ Test runner failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())