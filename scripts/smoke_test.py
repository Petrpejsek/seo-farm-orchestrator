#!/usr/bin/env python3
"""
SEO Farm Orchestrator - Smoke Test
Kompletní end-to-end test pipeline workflow

Usage: python scripts/smoke_test.py [--api-url http://localhost:8000] [--timeout 1500]
"""

import json
import time
import sys
import argparse
from urllib.request import urlopen, Request
from urllib.parse import quote
from urllib.error import HTTPError, URLError

class SmokeTest:
    def __init__(self, api_base_url="http://localhost:8000", timeout_seconds=1500):
        self.api_base_url = api_base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()
        
    def log(self, message, level="INFO"):
        """Strukturované logování s časovými razítky"""
        elapsed = time.time() - self.start_time
        print(f"[{elapsed:6.1f}s] {level:5s} | {message}")
        
    def make_request(self, method, endpoint, data=None):
        """HTTP request wrapper s error handlingem"""
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            if method == "POST":
                req_data = json.dumps(data).encode('utf-8') if data else None
                req = Request(url, data=req_data, headers={'Content-Type': 'application/json'})
                req.get_method = lambda: 'POST'
            else:
                req = Request(url)
                
            with urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
                
        except HTTPError as e:
            error_body = e.read().decode('utf-8')
            self.log(f"HTTP {e.code} Error: {error_body}", "ERROR")
            raise
        except URLError as e:
            self.log(f"URL Error: {str(e)}", "ERROR")
            raise
        except Exception as e:
            self.log(f"Request Error: {str(e)}", "ERROR")
            raise
            
    def start_workflow(self, topic):
        """Spustí workflow s daným tématem"""
        self.log(f"🚀 Starting workflow with topic: '{topic}'")
        
        response = self.make_request("POST", "/api/pipeline-run", {
            "topic": topic
        })
        
        if response.get("status") != "started":
            raise Exception(f"Unexpected response: {response}")
            
        workflow_id = response["workflow_id"]
        run_id = response["run_id"]
        
        self.log(f"✅ Workflow started: {workflow_id[:16]}... | {run_id[:16]}...")
        return workflow_id, run_id
        
    def check_workflow_status(self, workflow_id, run_id):
        """Zkontroluje status workflow a vrátí detailní informace"""
        encoded_workflow_id = quote(workflow_id, safe='')
        encoded_run_id = quote(run_id, safe='')
        
        response = self.make_request("GET", f"/api/workflow-result/{encoded_workflow_id}/{encoded_run_id}")
        
        status = response.get("status", "UNKNOWN")
        current_phase = response.get("current_phase", "Unknown")
        elapsed_seconds = response.get("elapsed_seconds", 0)
        stage_logs = response.get("stage_logs", [])
        
        return {
            "status": status,
            "current_phase": current_phase,
            "elapsed_seconds": elapsed_seconds,
            "stage_logs": stage_logs,
            "response": response
        }
        
    def wait_for_completion(self, workflow_id, run_id):
        """Čeká na dokončení workflow s periodickým checkováním"""
        self.log(f"⏳ Waiting for workflow completion (timeout: {self.timeout_seconds}s)")
        
        check_interval = 10  # Check každých 10 sekund
        last_logged_phase = None
        
        while True:
            current_time = time.time()
            elapsed_total = current_time - self.start_time
            
            if elapsed_total > self.timeout_seconds:
                self.log(f"❌ TIMEOUT: Workflow didn't complete within {self.timeout_seconds}s", "ERROR")
                return False, {"status": "TIMEOUT", "reason": "Test timeout reached"}
                
            try:
                status_info = self.check_workflow_status(workflow_id, run_id)
                status = status_info["status"]
                current_phase = status_info["current_phase"]
                workflow_elapsed = status_info["elapsed_seconds"]
                stage_logs = status_info["stage_logs"]
                
                # Log phase changes
                if current_phase != last_logged_phase:
                    self.log(f"🔄 Phase: {current_phase} (workflow elapsed: {workflow_elapsed}s)")
                    last_logged_phase = current_phase
                    
                # Log stage progress
                completed_stages = len([log for log in stage_logs if log.get("status") == "COMPLETED"])
                if stage_logs:
                    self.log(f"📊 Progress: {completed_stages}/{len(stage_logs)} stages completed")
                
                if status == "COMPLETED":
                    self.log(f"🎉 SUCCESS: Workflow completed in {workflow_elapsed}s")
                    return True, status_info["response"]
                    
                elif status in ["FAILED", "TERMINATED", "TIMED_OUT"]:
                    self.log(f"❌ FAILED: Workflow ended with status {status}", "ERROR")
                    
                    # Log failure details
                    if "failure_details" in status_info["response"]:
                        failure = status_info["response"]["failure_details"]
                        if failure:
                            self.log(f"💥 Failure: {failure.get('message', 'Unknown error')}", "ERROR")
                    
                    # Log last stage
                    if stage_logs:
                        last_stage = stage_logs[-1]
                        if last_stage.get("status") == "FAILED":
                            self.log(f"💥 Failed stage: {last_stage.get('stage')} - {last_stage.get('error', 'Unknown error')}", "ERROR")
                    
                    return False, status_info["response"]
                    
                elif status == "RUNNING":
                    # Continue waiting
                    time.sleep(check_interval)
                    continue
                    
                else:
                    self.log(f"⚠️  Unknown status: {status}", "WARN")
                    time.sleep(check_interval)
                    continue
                    
            except Exception as e:
                self.log(f"❌ Error checking status: {str(e)}", "ERROR")
                time.sleep(check_interval)
                continue
                
    def validate_result(self, result):
        """Validuje finální výsledek workflow"""
        self.log("🔍 Validating workflow result...")
        
        if not isinstance(result, dict):
            self.log(f"❌ Result is not a dict: {type(result)}", "ERROR")
            return False
            
        required_fields = ["topic", "workflow_id", "run_id"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            self.log(f"❌ Missing required fields: {missing_fields}", "ERROR")
            return False
            
        # Check for content
        if "generated" not in result or not result["generated"]:
            self.log("❌ No generated content found", "ERROR")
            return False
            
        # Check stage logs
        stage_logs = result.get("stage_logs", [])
        if not stage_logs:
            self.log("⚠️  No stage logs found", "WARN")
        else:
            completed_stages = [log for log in stage_logs if log.get("status") == "COMPLETED"]
            self.log(f"📊 Stages completed: {len(completed_stages)}/{len(stage_logs)}")
            
        self.log("✅ Result validation passed")
        return True
        
    def run_test(self):
        """Spustí kompletní smoke test"""
        timestamp = int(time.time())
        topic = f"smoke_test_{timestamp}"
        
        self.log("🧪 SEO Farm Orchestrator - Smoke Test Started")
        self.log(f"📍 API Base URL: {self.api_base_url}")
        self.log(f"⏰ Timeout: {self.timeout_seconds}s")
        
        try:
            # 1. Start workflow
            workflow_id, run_id = self.start_workflow(topic)
            
            # 2. Wait for completion
            success, result = self.wait_for_completion(workflow_id, run_id)
            
            if not success:
                self.log("❌ SMOKE TEST FAILED: Workflow did not complete successfully", "ERROR")
                return 1
                
            # 3. Validate result
            if not self.validate_result(result):
                self.log("❌ SMOKE TEST FAILED: Result validation failed", "ERROR")
                return 1
                
            # 4. Success summary
            total_time = time.time() - self.start_time
            self.log(f"🎉 SMOKE TEST PASSED: Total time {total_time:.1f}s")
            
            # Print summary
            if "stage_logs" in result:
                self.log("📈 Stage Summary:")
                for stage_log in result["stage_logs"]:
                    stage_name = stage_log.get("stage", "unknown")
                    stage_status = stage_log.get("status", "unknown")
                    stage_duration = stage_log.get("duration", 0)
                    self.log(f"  - {stage_name}: {stage_status} ({stage_duration:.1f}s)")
                    
            return 0
            
        except KeyboardInterrupt:
            self.log("⚠️  Test interrupted by user", "WARN")
            return 130
        except Exception as e:
            self.log(f"❌ SMOKE TEST FAILED: {str(e)}", "ERROR")
            return 1


def main():
    parser = argparse.ArgumentParser(description="SEO Farm Orchestrator Smoke Test")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                       help="Base URL for API (default: http://localhost:8000)")
    parser.add_argument("--timeout", type=int, default=1500,
                       help="Timeout in seconds (default: 1500 = 25 minutes)")
    
    args = parser.parse_args()
    
    test = SmokeTest(api_base_url=args.api_url, timeout_seconds=args.timeout)
    exit_code = test.run_test()
    sys.exit(exit_code)


if __name__ == "__main__":
    main() 