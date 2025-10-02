#!/usr/bin/env python3
"""
BusinessFlow AI - Real-Time Business Process Automation
Core application for intelligent workflow automation
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import sqlite3
import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Workflow:
    """Represents a business workflow"""
    id: str
    name: str
    description: str
    triggers: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    is_active: bool = True
    created_at: datetime = None
    last_triggered: Optional[datetime] = None

@dataclass
class Automation:
    """Represents an automation rule"""
    id: str
    workflow_id: str
    condition: str
    action: str
    parameters: Dict[str, Any]
    is_enabled: bool = True

class BusinessFlowAI:
    """Main BusinessFlow AI application"""
    
    def __init__(self, db_path: str = "businessflow.db"):
        self.db_path = db_path
        self.workflows = {}
        self.automations = {}
        self.integrations = {}
        self.init_database()
        self.setup_integrations()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                triggers TEXT,
                actions TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_triggered TIMESTAMP
            )
        """)
        
        # Create automations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS automations (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                condition TEXT,
                action TEXT,
                parameters TEXT,
                is_enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        """)
        
        # Create execution log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT,
                automation_id TEXT,
                status TEXT,
                message TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES workflows (id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def setup_integrations(self):
        """Setup integrations with business tools"""
        self.integrations = {
            "gmail": {
                "name": "Gmail",
                "type": "email",
                "endpoint": "https://gmail.googleapis.com/gmail/v1",
                "auth_type": "oauth2"
            },
            "slack": {
                "name": "Slack",
                "type": "messaging",
                "endpoint": "https://slack.com/api",
                "auth_type": "bearer"
            },
            "calendar": {
                "name": "Google Calendar",
                "type": "calendar",
                "endpoint": "https://www.googleapis.com/calendar/v3",
                "auth_type": "oauth2"
            },
            "crm": {
                "name": "CRM Integration",
                "type": "crm",
                "endpoint": "custom",
                "auth_type": "api_key"
            }
        }
        logger.info(f"Setup {len(self.integrations)} integrations")
    
    async def create_workflow(self, name: str, description: str, 
                            triggers: List[Dict], actions: List[Dict]) -> Workflow:
        """Create a new workflow"""
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            triggers=triggers,
            actions=actions,
            created_at=datetime.now()
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO workflows (id, name, description, triggers, actions)
            VALUES (?, ?, ?, ?, ?)
        """, (
            workflow.id,
            workflow.name,
            workflow.description,
            json.dumps(triggers),
            json.dumps(actions)
        ))
        
        conn.commit()
        conn.close()
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created workflow: {workflow.name}")
        return workflow
    
    async def detect_workflow_patterns(self, user_actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect potential workflow patterns from user actions"""
        patterns = []
        
        # Simple pattern detection (can be enhanced with ML)
        for i, action in enumerate(user_actions):
            if i < len(user_actions) - 1:
                next_action = user_actions[i + 1]
                
                # Check for repetitive patterns
                if (action.get('type') == next_action.get('type') and
                    action.get('app') == next_action.get('app')):
                    
                    pattern = {
                        'type': 'repetitive_action',
                        'app': action.get('app'),
                        'action': action.get('action'),
                        'frequency': 2,  # Would be calculated from full dataset
                        'confidence': 0.7
                    }
                    patterns.append(pattern)
        
        return patterns
    
    async def execute_automation(self, automation: Automation, context: Dict[str, Any]) -> bool:
        """Execute an automation rule"""
        try:
            # Check condition
            if not self.evaluate_condition(automation.condition, context):
                return False
            
            # Execute action
            result = await self.execute_action(automation.action, automation.parameters, context)
            
            # Log execution
            self.log_execution(automation.workflow_id, automation.id, "success", "Automation executed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Automation execution failed: {str(e)}")
            self.log_execution(automation.workflow_id, automation.id, "error", str(e))
            return False
    
    def evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate automation condition"""
        # Simple condition evaluation (can be enhanced)
        try:
            # Replace variables in condition with context values
            for key, value in context.items():
                condition = condition.replace(f"{{{key}}}", str(value))
            
            # Evaluate condition (simplified)
            return eval(condition)
        except:
            return False
    
    async def execute_action(self, action: str, parameters: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute automation action"""
        if action == "send_email":
            return await self.send_email(parameters, context)
        elif action == "create_calendar_event":
            return await self.create_calendar_event(parameters, context)
        elif action == "send_slack_message":
            return await self.send_slack_message(parameters, context)
        elif action == "update_crm":
            return await self.update_crm(parameters, context)
        else:
            logger.warning(f"Unknown action: {action}")
            return None
    
    async def send_email(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Send email via Gmail API"""
        # Implementation would use Gmail API
        logger.info(f"Sending email: {parameters.get('subject', 'No subject')}")
        return True
    
    async def create_calendar_event(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Create calendar event"""
        # Implementation would use Calendar API
        logger.info(f"Creating calendar event: {parameters.get('title', 'No title')}")
        return True
    
    async def send_slack_message(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Send Slack message"""
        # Implementation would use Slack API
        logger.info(f"Sending Slack message: {parameters.get('message', 'No message')}")
        return True
    
    async def update_crm(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Update CRM record"""
        # Implementation would use CRM API
        logger.info(f"Updating CRM: {parameters.get('record_type', 'Unknown')}")
        return True
    
    def log_execution(self, workflow_id: str, automation_id: str, status: str, message: str):
        """Log automation execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO execution_log (workflow_id, automation_id, status, message)
            VALUES (?, ?, ?, ?)
        """, (workflow_id, automation_id, status, message))
        
        conn.commit()
        conn.close()
    
    async def get_workflow_analytics(self, workflow_id: str) -> Dict[str, Any]:
        """Get analytics for a workflow"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get execution statistics
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM execution_log
            WHERE workflow_id = ?
            GROUP BY status
        """, (workflow_id,))
        
        stats = dict(cursor.fetchall())
        
        # Get recent executions
        cursor.execute("""
            SELECT status, message, executed_at
            FROM execution_log
            WHERE workflow_id = ?
            ORDER BY executed_at DESC
            LIMIT 10
        """, (workflow_id,))
        
        recent = cursor.fetchall()
        
        conn.close()
        
        return {
            "workflow_id": workflow_id,
            "statistics": stats,
            "recent_executions": recent,
            "success_rate": stats.get("success", 0) / max(sum(stats.values()), 1)
        }

async def main():
    """Main function to demonstrate BusinessFlow AI"""
    print("🚀 BusinessFlow AI - Real-Time Business Process Automation")
    print("=" * 60)
    
    # Initialize the system
    bf_ai = BusinessFlowAI()
    
    # Create sample workflow
    sample_workflow = await bf_ai.create_workflow(
        name="Email Follow-up Automation",
        description="Automatically follow up on emails after 3 days",
        triggers=[
            {"type": "email_received", "from": "client@company.com", "subject_contains": "proposal"}
        ],
        actions=[
            {"type": "send_email", "to": "{{sender}}", "subject": "Follow-up on Proposal", "body": "Hi, just checking on the proposal we sent..."}
        ]
    )
    
    print(f"✅ Created workflow: {sample_workflow.name}")
    print(f"   ID: {sample_workflow.id}")
    print(f"   Triggers: {len(sample_workflow.triggers)}")
    print(f"   Actions: {len(sample_workflow.actions)}")
    
    # Simulate workflow pattern detection
    user_actions = [
        {"type": "email", "app": "gmail", "action": "send", "timestamp": datetime.now()},
        {"type": "email", "app": "gmail", "action": "send", "timestamp": datetime.now()},
        {"type": "calendar", "app": "google", "action": "create_event", "timestamp": datetime.now()}
    ]
    
    patterns = await bf_ai.detect_workflow_patterns(user_actions)
    print(f"\n🔍 Detected {len(patterns)} workflow patterns")
    
    for pattern in patterns:
        print(f"   - {pattern['type']}: {pattern['app']} ({pattern['confidence']:.1%} confidence)")
    
    # Get analytics
    analytics = await bf_ai.get_workflow_analytics(sample_workflow.id)
    print(f"\n📊 Workflow Analytics:")
    print(f"   Success Rate: {analytics['success_rate']:.1%}")
    print(f"   Total Executions: {sum(analytics['statistics'].values())}")
    
    print(f"\n🎯 BusinessFlow AI is ready for business process automation!")
    print(f"   Market Opportunity: $21.7B by 2027")
    print(f"   Target: SMB market (currently underserved)")

# FastAPI Application
app = FastAPI(
    title="BusinessFlow AI",
    description="Real-Time Business Process Automation Platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global BusinessFlow AI instance
bf_ai = None

@app.on_event("startup")
async def startup_event():
    """Initialize BusinessFlow AI on startup"""
    global bf_ai
    bf_ai = BusinessFlowAI()
    await bf_ai.initialize()
    logger.info("BusinessFlow AI initialized successfully")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "BusinessFlow AI - Real-Time Business Process Automation",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "BusinessFlow AI"
    }

@app.get("/workflows")
async def get_workflows():
    """Get all workflows"""
    if not bf_ai:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    workflows = list(bf_ai.workflows.values())
    return {"workflows": workflows}

@app.post("/workflows")
async def create_workflow(workflow_data: dict):
    """Create a new workflow"""
    if not bf_ai:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        workflow = await bf_ai.create_workflow(
            name=workflow_data["name"],
            description=workflow_data["description"],
            triggers=workflow_data.get("triggers", []),
            actions=workflow_data.get("actions", [])
        )
        return {"workflow": workflow, "message": "Workflow created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/analytics")
async def get_analytics():
    """Get system analytics"""
    if not bf_ai:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        analytics = await bf_ai.get_system_analytics()
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # For local development
    asyncio.run(main())
    
    # For production deployment
    uvicorn.run(app, host="0.0.0.0", port=8000)
