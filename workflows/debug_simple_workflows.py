#!/usr/bin/env python3
"""
🔍 SIMPLE DEBUG WORKFLOWS
=========================

Zjednodušené workflow pro testování jednotlivých komponent:
- Single assistant test workflow
- Database test workflow  
- Image generation test workflow
- Publish script test workflow
- Connection test workflow

Každý workflow testuje jednu specifickou funkcionalitu izolovaně.
"""

import os
import json
from datetime import timedelta
from typing import Dict, Any, Optional, List
from temporalio import workflow

# Import debugging nástrojů
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from helpers.db_logger import db_logger
from helpers.db_connection_audit import run_connection_audit
from helpers.db_activity_monitor import start_database_monitoring, get_database_health_report


@workflow.defn
class SingleAssistantTestWorkflow:
    """Test workflow pro jednotlivého asistenta"""
    
    @workflow.run
    async def run(self, assistant_config: Dict[str, Any], test_input: str) -> Dict[str, Any]:
        """
        Testuje jediného asistenta izolovaně
        
        Args:
            assistant_config: Konfigurace asistenta
            test_input: Testovací vstup
            
        Returns:
            Výsledek testu asistenta
        """
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info(f"🧪 SINGLE_ASSISTANT_TEST_START: {assistant_config.get('name', 'Unknown')}")
        
        test_result = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "assistant_name": assistant_config.get("name", "Unknown"),
            "function_key": assistant_config.get("function_key", "unknown"),
            "test_input": test_input,
            "timestamp": workflow.now().timestamp()
        }
        
        try:
            # Test základní activity pro asistenta
            workflow.logger.info(f"🔧 Testing assistant: {assistant_config.get('name')}")
            
            assistant_result = await workflow.execute_activity(
                "execute_assistant",
                {
                    "assistant_config": assistant_config,
                    "topic": test_input,
                    "current_date": workflow.now().isoformat(),
                    "previous_outputs": {}
                },
                start_to_close_timeout=timedelta(minutes=5),
                schedule_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=1)
            )
            
            test_result.update({
                "success": True,
                "result": assistant_result,
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.info(f"✅ SINGLE_ASSISTANT_TEST_SUCCESS: {assistant_config.get('name')}")
            return test_result
            
        except Exception as e:
            test_result.update({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.error(f"❌ SINGLE_ASSISTANT_TEST_FAILED: {assistant_config.get('name')} - {e}")
            return test_result


@workflow.defn
class DatabaseTestWorkflow:
    """Test workflow pro databázové operace"""
    
    @workflow.run
    async def run(self, test_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Testuje databázové připojení a operace
        
        Args:
            test_config: Konfigurace testů
            
        Returns:
            Výsledky databázových testů
        """
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info("🔍 DATABASE_TEST_WORKFLOW_START")
        
        test_result = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "test_type": "database",
            "timestamp": workflow.now().timestamp(),
            "config": test_config or {}
        }
        
        try:
            # Test DB debug assistant
            workflow.logger.info("🔧 Running database debug tests...")
            
            db_test_result = await workflow.execute_activity(
                "db_debug_assistant",
                test_config or {"comprehensive": True},
                start_to_close_timeout=timedelta(minutes=3),
                schedule_to_close_timeout=timedelta(minutes=5),
                heartbeat_timeout=timedelta(seconds=30)
            )
            
            test_result.update({
                "success": db_test_result.get("summary", {}).get("overall_success", False),
                "db_tests": db_test_result,
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.info(f"✅ DATABASE_TEST_WORKFLOW_SUCCESS: {db_test_result.get('summary', {}).get('success_count', 0)} tests passed")
            return test_result
            
        except Exception as e:
            test_result.update({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.error(f"❌ DATABASE_TEST_WORKFLOW_FAILED: {e}")
            return test_result


@workflow.defn
class ImageGenerationTestWorkflow:
    """Test workflow pro generování obrázků"""
    
    @workflow.run
    async def run(self, test_prompts: list = None) -> Dict[str, Any]:
        """
        Testuje generování obrázků izolovaně
        
        Args:
            test_prompts: Seznam test promptů
            
        Returns:
            Výsledky testů generování obrázků
        """
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info("🎨 IMAGE_GENERATION_TEST_WORKFLOW_START")
        
        # Default test prompts
        if not test_prompts:
            test_prompts = [
                "A simple red circle on white background",
                "Blue square with text 'TEST'",
                "Green triangle, minimalist style"
            ]
        
        test_result = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "test_type": "image_generation",
            "timestamp": workflow.now().timestamp(),
            "test_prompts": test_prompts,
            "results": []
        }
        
        try:
            # Načtení ImageRenderer konfigurace
            workflow.logger.info("📋 Loading ImageRenderer configuration...")
            
            assistants_config = await workflow.execute_activity(
                "load_assistants_from_database",
                "default_project_id",  # TODO: Use actual project ID
                schedule_to_close_timeout=timedelta(seconds=30),
                heartbeat_timeout=timedelta(seconds=10)
            )
            
            # Najít ImageRenderer
            assistants = assistants_config.get("assistants", [])
            image_renderer = None
            for assistant in assistants:
                if assistant.get("function_key") == "image_renderer_assistant":
                    image_renderer = assistant
                    break
            
            if not image_renderer:
                raise Exception("ImageRenderer assistant not found in database")
            
            # Test generování pro každý prompt
            for i, prompt in enumerate(test_prompts):
                workflow.logger.info(f"🎨 Testing image generation {i+1}/{len(test_prompts)}: {prompt[:50]}...")
                
                try:
                    # Vytvoř multimedia návrhy pro ImageRenderer
                    multimedia_input = {
                        "suggestions": [
                            {
                                "type": "image",
                                "prompt": prompt,
                                "style": "test image",
                                "priority": "high"
                            }
                        ]
                    }
                    
                    image_result = await workflow.execute_activity(
                        "execute_assistant",
                        {
                            "assistant_config": image_renderer,
                            "topic": multimedia_input,
                            "current_date": workflow.now().isoformat(),
                            "previous_outputs": {}
                        },
                        start_to_close_timeout=timedelta(minutes=3),
                        schedule_to_close_timeout=timedelta(minutes=5),
                        heartbeat_timeout=timedelta(seconds=30)
                    )
                    
                    test_result["results"].append({
                        "prompt": prompt,
                        "success": True,
                        "result": image_result,
                        "images_generated": len(image_result.get("output", {}).get("images", [])) if image_result.get("output") else 0
                    })
                    
                except Exception as e:
                    test_result["results"].append({
                        "prompt": prompt,
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    workflow.logger.error(f"❌ Image generation failed for prompt {i+1}: {e}")
            
            # Celkové vyhodnocení
            successful_tests = sum(1 for result in test_result["results"] if result["success"])
            test_result.update({
                "success": successful_tests > 0,
                "successful_tests": successful_tests,
                "total_tests": len(test_prompts),
                "success_rate": successful_tests / len(test_prompts),
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.info(f"✅ IMAGE_GENERATION_TEST_WORKFLOW_COMPLETE: {successful_tests}/{len(test_prompts)} tests passed")
            return test_result
            
        except Exception as e:
            test_result.update({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.error(f"❌ IMAGE_GENERATION_TEST_WORKFLOW_FAILED: {e}")
            return test_result


@workflow.defn
class PublishScriptTestWorkflow:
    """Test workflow pro publish script"""
    
    @workflow.run
    async def run(self, mock_pipeline_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Testuje publish script izolovaně
        
        Args:
            mock_pipeline_data: Mock data z pipeline
            
        Returns:
            Výsledky testu publish scriptu
        """
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info("🚀 PUBLISH_SCRIPT_TEST_WORKFLOW_START")
        
        # Default mock data
        if not mock_pipeline_data:
            mock_pipeline_data = {
                "brief_assistant_output": "Test brief about testing",
                "research_assistant_output": "Test research data",
                "fact_validator_assistant_output": "Facts validated",
                "draft_assistant_output": "# Test Article\n\nThis is a test article.",
                "humanizer_assistant_output": "Humanized test content",
                "seo_assistant_output": {"title": "Test Article", "meta_description": "Test description", "keywords": ["test", "article"]},
                "multimedia_assistant_output": {"suggestions": [{"type": "image", "prompt": "test image"}]},
                "qa_assistant_output": {"questions": [{"question": "Test?", "answer": "Yes"}]},
                "image_renderer_assistant_output": {"images": [{"url": "test.jpg", "prompt": "test"}]}
            }
        
        test_result = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "test_type": "publish_script",
            "timestamp": workflow.now().timestamp(),
            "mock_data_keys": list(mock_pipeline_data.keys())
        }
        
        try:
            # Test publish activity
            workflow.logger.info("🔧 Testing publish script...")
            
            publish_result = await workflow.execute_activity(
                "publish_activity",
                {
                    "assistant_config": {"name": "PublishScript", "function_key": "publish_script"},
                    "topic": mock_pipeline_data,
                    "current_date": workflow.now().isoformat(),
                    "previous_outputs": mock_pipeline_data
                },
                start_to_close_timeout=timedelta(minutes=2),
                schedule_to_close_timeout=timedelta(minutes=3),
                heartbeat_timeout=timedelta(seconds=30)
            )
            
            test_result.update({
                "success": publish_result.get("success", False),
                "result": publish_result,
                "formats_generated": publish_result.get("formats_generated", []),
                "files_saved": len(publish_result.get("files_saved", [])),
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.info(f"✅ PUBLISH_SCRIPT_TEST_WORKFLOW_SUCCESS: {len(publish_result.get('formats_generated', []))} formats generated")
            return test_result
            
        except Exception as e:
            test_result.update({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.error(f"❌ PUBLISH_SCRIPT_TEST_WORKFLOW_FAILED: {e}")
            return test_result


@workflow.defn
class ConnectionTestWorkflow:
    """Test workflow pro databázové konexe"""
    
    @workflow.run
    async def run(self, connection_tests: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Testuje databázové konexe a performance
        
        Args:
            connection_tests: Konfigurace testů
            
        Returns:
            Výsledky testů konexí
        """
        workflow_id = workflow.info().workflow_id
        run_id = workflow.info().run_id
        
        workflow.logger.info("🔗 CONNECTION_TEST_WORKFLOW_START")
        
        test_result = {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "test_type": "connections",
            "timestamp": workflow.now().timestamp(),
            "config": connection_tests or {}
        }
        
        try:
            # Test různých typů konexí současně
            workflow.logger.info("🔧 Testing multiple connection scenarios...")
            
            # Test 1: Základní konexe
            basic_result = await workflow.execute_activity(
                "db_debug_assistant",
                {"test_mode": "basic_connectivity"},
                start_to_close_timeout=timedelta(seconds=30),
                schedule_to_close_timeout=timedelta(minutes=1),
                heartbeat_timeout=timedelta(seconds=10)
            )
            
            # Test 2: Load assistants (typická operace)
            assistants_result = await workflow.execute_activity(
                "load_assistants_from_database", 
                "default_project_id",
                schedule_to_close_timeout=timedelta(seconds=30),
                heartbeat_timeout=timedelta(seconds=10)
            )
            
            # Test 3: Concurrent operations (více aktivit najednou)
            concurrent_tests = []
            for i in range(3):
                concurrent_tests.append(
                    workflow.execute_activity(
                        "db_debug_assistant",
                        {"test_mode": f"concurrent_{i}"},
                        start_to_close_timeout=timedelta(seconds=30),
                        schedule_to_close_timeout=timedelta(minutes=1),
                        heartbeat_timeout=timedelta(seconds=10)
                    )
                )
            
            # Počkat na dokončení všech concurrent testů
            concurrent_results = []
            for test in concurrent_tests:
                try:
                    result = await test
                    concurrent_results.append({"success": True, "result": result})
                except Exception as e:
                    concurrent_results.append({"success": False, "error": str(e)})
            
            # Vyhodnocení výsledků
            successful_concurrent = sum(1 for r in concurrent_results if r["success"])
            
            test_result.update({
                "success": basic_result.get("summary", {}).get("overall_success", False) and len(assistants_result.get("assistants", [])) > 0,
                "tests": {
                    "basic_connectivity": basic_result,
                    "load_assistants": {
                        "success": len(assistants_result.get("assistants", [])) > 0,
                        "assistants_count": len(assistants_result.get("assistants", [])),
                        "result": assistants_result
                    },
                    "concurrent_operations": {
                        "success": successful_concurrent == 3,
                        "successful_count": successful_concurrent,
                        "total_count": 3,
                        "results": concurrent_results
                    }
                },
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.info(f"✅ CONNECTION_TEST_WORKFLOW_SUCCESS: {successful_concurrent}/3 concurrent tests passed")
            return test_result
            
        except Exception as e:
            test_result.update({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": workflow.now().timestamp() - test_result["timestamp"]
            })
            
            workflow.logger.error(f"❌ CONNECTION_TEST_WORKFLOW_FAILED: {e}")
            return test_result


# Utility funkce pro snadné spouštění testů
def create_single_assistant_test_config(assistant_name: str, test_input: str = "Test vstup") -> Dict[str, Any]:
    """Vytvoří konfiguraci pro test jednotlivého asistenta"""
    assistant_configs = {
        "brief_assistant": {
            "name": "BriefAssistant",
            "function_key": "brief_assistant",
            "order": 1
        },
        "research_assistant": {
            "name": "ResearchAssistant", 
            "function_key": "research_assistant",
            "order": 2
        },
        "image_renderer_assistant": {
            "name": "ImageRendererAssistant",
            "function_key": "image_renderer_assistant", 
            "order": 9
        }
    }
    
    return {
        "assistant_config": assistant_configs.get(assistant_name, {
            "name": assistant_name,
            "function_key": assistant_name,
            "order": 1
        }),
        "test_input": test_input
    }


def create_comprehensive_test_suite() -> List[Dict[str, Any]]:
    """Vytvoří kompletní sadu testů pro debugging"""
    return [
        {
            "workflow": "DatabaseTestWorkflow",
            "config": {"comprehensive": True},
            "description": "Kompletní test databázových operací"
        },
        {
            "workflow": "ConnectionTestWorkflow", 
            "config": {"concurrent_tests": 3},
            "description": "Test databázových konexí a concurrent operací"
        },
        {
            "workflow": "ImageGenerationTestWorkflow",
            "config": {"test_prompts": ["Simple test image", "Red circle"]},
            "description": "Test generování obrázků"
        },
        {
            "workflow": "PublishScriptTestWorkflow",
            "config": {},
            "description": "Test publish scriptu s mock daty"
        },
        {
            "workflow": "SingleAssistantTestWorkflow",
            "config": create_single_assistant_test_config("brief_assistant", "Test článek o testování"),
            "description": "Test BriefAssistant"
        }
    ]


if __name__ == "__main__":
    print("🔍 Simple Debug Workflows ready for use")
    print("\nAvailable workflows:")
    print("1. SingleAssistantTestWorkflow - Test individual assistant")
    print("2. DatabaseTestWorkflow - Test database operations")
    print("3. ImageGenerationTestWorkflow - Test image generation")
    print("4. PublishScriptTestWorkflow - Test publish script")
    print("5. ConnectionTestWorkflow - Test database connections")
    
    test_suite = create_comprehensive_test_suite()
    print(f"\n✅ Comprehensive test suite ready with {len(test_suite)} tests")