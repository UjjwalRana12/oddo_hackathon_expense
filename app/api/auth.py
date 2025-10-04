from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import secrets
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from ..core.database import get_db
from ..core.security import get_password_hash, verify_password, create_access_token
from ..models.models import User, Company, UserRole
from ..schemas.schemas import Token, LoginRequest, SignupRequest, User as UserSchema, ForgotPasswordRequest, ResetPasswordRequest, SuccessResponse
from ..services.currency_service import currency_service

router = APIRouter()

# In-memory store for reset tokens (in production, use Redis or database)
reset_tokens = {}

@router.post("/signup", response_model=Token)
async def signup(signup_data: SignupRequest, db: Session = Depends(get_db)):
    """
    Create new user account with company
    """
    try:
        # Check if user already exists
        db_user = db.query(User).filter(User.email == signup_data.email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Get country currency
        try:
            countries = await currency_service.get_countries()
            country_currency = None
            
            for country in countries:
                if country.name.lower() == signup_data.country.lower():
                    # Get the first currency for the country
                    if country.currencies:
                        country_currency = list(country.currencies.keys())[0]
                    break
            
            if not country_currency:
                country_currency = "USD"  # Default fallback
                
        except Exception as e:
            print(f"Warning: Could not fetch currency for {signup_data.country}, using USD")
            country_currency = "USD"
        
        # Create company
        db_company = Company(
            name=signup_data.company_name,
            country=signup_data.country,
            currency=country_currency
        )
        db.add(db_company)
        db.commit()
        db.refresh(db_company)
        
        # Split full_name into first_name and last_name
        name_parts = signup_data.full_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Create admin user
        hashed_password = get_password_hash(signup_data.password)
        db_user = User(
            email=signup_data.email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.ADMIN,
            company_id=db_company.id,
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Create access token
        access_token_expires = timedelta(minutes=30)  # You can get this from settings
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        
        # Convert db_user to schema
        user_schema = UserSchema(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,  # This uses the @property in the model
            role=db_user.role,
            is_active=db_user.is_active,
            company_id=db_user.company_id,
            manager_id=db_user.manager_id,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_schema
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating account: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    User login
    """
    try:
        # Find user
        db_user = db.query(User).filter(User.email == login_data.email).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(login_data.password, db_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if user is active
        if not db_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=30)  # You can get this from settings
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        
        # Convert db_user to schema
        user_schema = UserSchema(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,  # This uses the @property in the model
            role=db_user.role,
            is_active=db_user.is_active,
            company_id=db_user.company_id,
            manager_id=db_user.manager_id,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_schema
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )

@router.post("/forgot-password", response_model=SuccessResponse)
async def forgot_password(forgot_data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Send password reset email to user
    """
    try:
        # Find user by email
        db_user = db.query(User).filter(User.email == forgot_data.email).first()
        
        # Always return success to prevent email enumeration attacks
        if not db_user:
            return SuccessResponse(
                message="If an account with that email exists, a password reset link has been sent.",
                data={"email": forgot_data.email}
            )
        
        # Generate reset token (6-digit code)
        reset_token = str(secrets.randbelow(900000) + 100000)  # Generates 6-digit number
        
        # Store token with expiration (15 minutes)
        reset_tokens[forgot_data.email] = {
            "token": reset_token,
            "expires_at": datetime.utcnow() + timedelta(minutes=15),
            "user_id": db_user.id
        }
        
        # Send email (you can customize this based on your email service)
        try:
            await send_reset_password_email(db_user.email, db_user.full_name, reset_token)
            email_sent = True
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            # For demo purposes, we'll log the token
            print(f"🔑 Password reset token for {forgot_data.email}: {reset_token}")
            email_sent = False
        
        return SuccessResponse(
            message="If an account with that email exists, a password reset link has been sent.",
            data={
                "email": forgot_data.email,
                "email_sent": email_sent,
                "demo_token": reset_token if not email_sent else None  # Only for development
            }
        )
        
    except Exception as e:
        print(f"Error in forgot password: {str(e)}")
        return SuccessResponse(
            message="If an account with that email exists, a password reset link has been sent.",
            data={"email": forgot_data.email}
        )

@router.post("/reset-password", response_model=SuccessResponse)
async def reset_password(reset_data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset user password using token
    """
    try:
        # Check if token exists and is valid
        token_data = reset_tokens.get(reset_data.email)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Check if token matches
        if token_data["token"] != reset_data.token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Check if token is expired
        if datetime.utcnow() > token_data["expires_at"]:
            # Remove expired token
            del reset_tokens[reset_data.email]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one."
            )
        
        # Find user
        db_user = db.query(User).filter(User.id == token_data["user_id"]).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        hashed_password = get_password_hash(reset_data.new_password)
        db_user.hashed_password = hashed_password
        db_user.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Remove used token
        del reset_tokens[reset_data.email]
        
        return SuccessResponse(
            message="Password has been reset successfully",
            data={"email": reset_data.email}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting password: {str(e)}"
        )

@router.post("/verify-reset-token", response_model=SuccessResponse)
async def verify_reset_token(email: str, token: str):
    """
    Verify if reset token is valid (useful for frontend validation)
    """
    try:
        token_data = reset_tokens.get(email)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        if token_data["token"] != token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        if datetime.utcnow() > token_data["expires_at"]:
            del reset_tokens[email]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Calculate remaining time
        remaining_minutes = int((token_data["expires_at"] - datetime.utcnow()).total_seconds() / 60)
        
        return SuccessResponse(
            message="Token is valid",
            data={
                "email": email,
                "expires_in_minutes": remaining_minutes
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying token: {str(e)}"
        )

async def send_reset_password_email(email: str, full_name: str, reset_token: str):
    """
    Send password reset email (customize based on your email service)
    """
    # Email configuration (you should move these to environment variables)
    SMTP_SERVER = "smtp.gmail.com"  # Change to your email provider
    SMTP_PORT = 587
    EMAIL_USER = "your-email@gmail.com"  # Your email
    EMAIL_PASSWORD = "your-app-password"  # Your app password
    
    try:
        # Create message
        msg = MimeMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg['Subject'] = "Password Reset Request - Expense Management System"
        
        # Email body
        body = f"""
        Hi {full_name},
        
        You requested a password reset for your Expense Management System account.
        
        Your password reset code is: {reset_token}
        
        This code will expire in 15 minutes.
        
        If you didn't request this reset, please ignore this email.
        
        Best regards,
        Expense Management System Team
        """
        
        msg.attach(MimeText(body, 'plain'))
        
        # Connect to server and send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, email, text)
        server.quit()
        
        print(f"Password reset email sent to {email}")
        
    except Exception as e:
        print(f"Failed to send email to {email}: {str(e)}")
        raise e