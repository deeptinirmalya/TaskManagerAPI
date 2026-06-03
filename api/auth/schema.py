from pydantic import BaseModel, Field

class LoginSchema(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        description="The user's username or email address."
    )
    
    password: str = Field(
        ..., 
        max_length=128, 
        description="The user's password."
    )

    remember_me: bool = Field(
        default=False, 
        description="Whether to keep the user logged in after the session expires."
    )