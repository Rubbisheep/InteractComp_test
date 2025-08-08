# -*- coding: utf-8 -*-
# @Date    : 2025-03-31
# @Author  : Zhaoyang
# @Desc    : 

from typing import Dict, List, Tuple, Type, Optional, Union, Any

from pydantic import BaseModel, Field, create_model
import re

from abc import ABC, abstractmethod


class FormatError(Exception):
    """Exception raised when response format validation fails"""
    pass

class BaseFormatter(BaseModel):
    """Base class for all formatters"""
    
    @abstractmethod
    def prepare_prompt(self, prompt: str) -> str:
        """Prepare the prompt to instruct the LLM to return in the required format"""
        pass
    
    @abstractmethod
    def validate_response(self, response: str) -> Tuple[bool, Any]:
        """Validate if the response matches the expected format"""
        pass

    def format_error_message(self) -> str:
        """Return an error message for invalid format"""
        return f"Response did not match the expected {self.__class__.__name__} format"

class XmlFormatter(BaseFormatter):
    """Formatter for XML responses"""
    model: Optional[Type[BaseModel]] = None
    fields: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, fields_dict: Dict[str, str]) -> "XmlFormatter":
        """
        Create formatter from a dictionary of field names and descriptions
        
        Args:
            fields_dict: Dictionary where keys are field names and values are field descriptions
            
        Returns:
            An XmlFormatter instance configured with the specified fields
        """
        model_fields = {}
        for name, desc in fields_dict.items():
            model_fields[name] = (str, Field(default="", description=desc))
        
        model_class = create_model("XmlResponseModel", **model_fields)
        
        return cls(model=model_class)
    
    @classmethod
    def from_model(cls, model_class: Type[BaseModel]) -> "XmlFormatter":
        """
        Create formatter from an existing Pydantic model class
        
        Args:
            model_class: A Pydantic model class
            
        Returns:
            An XmlFormatter instance configured with the model's fields
        """
        return cls(model=model_class)
    
    def _get_field_names(self) -> List[str]:
        """Get field names from the model"""
        if self.model:
            return list(self.model.model_fields.keys())
        return []
    
    def _get_field_description(self, field_name: str) -> str:
        """Get field description from the model"""
        if self.model and field_name in self.model.model_fields:
            return self.model.model_fields[field_name].description
        return ""    
    
    def prepare_prompt(self, prompt: str) -> str:
        examples = []
        for field_name in self._get_field_names():
            description = self._get_field_description(field_name)
            examples.append(f"<{field_name}>{description}</{field_name}>")

        example_str = "\n".join(examples)
        
        instructions = prompt + f"\n# You can output anything, but in the final, you need to provide the following fields, and make sure to warp it with xml tags:\n{example_str}"
        return instructions
    
    def validate_response(self, response: str) -> Tuple[bool, dict]:
        """Validate if the response contains all required fields in XML format"""
        try:
            pattern = r"<(\w+)>(.*?)</\1>"
            matches = re.findall(pattern, response, re.DOTALL)
            
            found_fields = {match[0]: match[1].strip() for match in matches}
            
            for field_name in self._get_field_names():
                field = self.model.model_fields[field_name]
                is_required = field.default is None and field.default_factory is None
                
                if is_required and (field_name not in found_fields or not found_fields[field_name]):
                    raise FormatError(f"Field '{field_name}' is missing or empty.")

            return True, found_fields
        except Exception:
            return False, None
 
class TextFormatter(BaseFormatter):    
    def prepare_prompt(self, prompt: str) -> str:
        return prompt
    
    def validate_response(self, response: str) -> Tuple[bool, Union[str, None]]:
        """
        For plain text formatter, we simply return the response as is without validation
        since there are no format restrictions
        """
        return True, response
    