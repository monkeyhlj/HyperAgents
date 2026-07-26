"""Skill execution engine with sandboxing support."""

import asyncio
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import logging

from app.db.session import SessionLocal
from app.db.models import SkillExecutionModel, SkillMetadataModel
from app.runtime.skill_service import validate_input_output
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SkillExecutor:
    """Execute Skill with sandboxing support"""
    
    def __init__(self, skill_id: str, skill_metadata: Dict[str, Any], db: Optional[Session] = None):
        """
        Initialize skill executor
        
        Args:
            skill_id: Skill resource ID
            skill_metadata: Skill metadata dict (from SkillMetadataModel)
            db: Database session for tracking execution
        """
        self.skill_id = skill_id
        self.metadata = skill_metadata
        self.db = db
        self.temp_dir = None
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        execution_id: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> Dict[str, Any]:
        """
        Execute skill with provided input
        
        Args:
            input_data: Input dict (must conform to input_schema)
            execution_id: Optional execution record ID (for tracking)
            timeout_seconds: Max execution time (default 30s)
            
        Returns:
            Dict with status, output_data, and error_message (if any)
        """
        # Validate input against schema
        try:
            validate_input_output(input_data, self.metadata.get("input_schema"))
        except ValueError as e:
            return {
                "status": "failed",
                "error_message": f"Input validation failed: {str(e)}"
            }
        
        try:
            # Extract and setup skill code
            skill_dir = await self._extract_skill()
            
            # Execute skill code
            output_data = await self._execute_in_sandbox(
                skill_dir,
                input_data,
                timeout_seconds
            )
            
            # Validate output against schema
            try:
                validate_input_output(output_data, self.metadata.get("output_schema"))
            except ValueError as e:
                logger.warning(f"Output validation warning: {e}")
            
            result = {
                "status": "completed",
                "output_data": output_data,
            }
            
            # Record execution
            if execution_id and self.db:
                await self._record_execution(execution_id, "completed", output_data)
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Skill execution timeout after {timeout_seconds}s"
            if execution_id and self.db:
                await self._record_execution(execution_id, "failed", error_message=error_msg)
            return {
                "status": "failed",
                "error_message": error_msg
            }
        except Exception as e:
            error_msg = f"Skill execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            if execution_id and self.db:
                await self._record_execution(execution_id, "failed", error_message=error_msg)
            return {
                "status": "failed",
                "error_message": error_msg
            }
        finally:
            # Cleanup
            if self.temp_dir:
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def _extract_skill(self) -> str:
        """
        Extract skill code to temp directory
        
        TODO: Implement actual skill extraction from storage (local/git/s3)
        For now, returns placeholder path
        """
        self.temp_dir = tempfile.mkdtemp()
        return self.temp_dir
    
    async def _execute_in_sandbox(
        self,
        skill_dir: str,
        input_data: Dict[str, Any],
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """
        Execute skill code in isolated environment
        
        Currently supports:
        - Python venv execution (TODO: docker support)
        
        Args:
            skill_dir: Directory containing skill code
            input_data: Input parameters
            timeout_seconds: Execution timeout
            
        Returns:
            Output data from skill execution
        """
        # TODO: Implement proper sandboxing
        # For MVP: Direct execution with validation
        
        # Parse entrypoint: "scripts/main:execute"
        entrypoint = self.metadata.get("entrypoint", "scripts/main:execute")
        module_path, func_name = entrypoint.split(":")
        module_name = module_path.replace("/", ".").replace(".py", "")
        
        # TODO: Create isolated venv, install requirements, execute
        # For now, return mock result
        
        logger.info(f"[Skill] Executing {self.skill_id} with entrypoint {entrypoint}")
        
        # Mock execution (should be replaced with actual sandbox)
        return {
            "status": "mock",
            "message": "Skill execution not yet implemented",
            "input": input_data
        }
    
    async def _record_execution(
        self,
        execution_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """Record skill execution in database"""
        if not self.db:
            return
        
        execution = self.db.query(SkillExecutionModel).filter(
            SkillExecutionModel.id == execution_id
        ).first()
        
        if execution:
            execution.status = status
            execution.output_data = output_data
            execution.error_message = error_message
            self.db.commit()
            logger.info(f"[Skill] Recorded execution {execution_id}: {status}")


# Placeholder for future implementations

class PythonVenvExecutor(SkillExecutor):
    """Execute Skill in isolated Python virtual environment"""
    
    async def _execute_in_sandbox(
        self,
        skill_dir: str,
        input_data: Dict[str, Any],
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """
        Execute skill in Python venv
        
        TODO: Implementation
        - Create temporary venv
        - Install requirements
        - Execute entrypoint
        - Capture stdout/stderr
        - Cleanup venv
        """
        pass


class DockerExecutor(SkillExecutor):
    """Execute Skill in Docker container"""
    
    async def _execute_in_sandbox(
        self,
        skill_dir: str,
        input_data: Dict[str, Any],
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """
        Execute skill in Docker container
        
        TODO: Implementation
        - Build container image
        - Run with resource limits
        - Mount skill directory
        - Cleanup container
        """
        pass
