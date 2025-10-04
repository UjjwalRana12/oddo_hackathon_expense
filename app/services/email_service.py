import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Optional
import os

class EmailService:
    def __init__(self):
        # Email configuration (you should move these to environment variables)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER", "your-email@gmail.com")
        self.email_password = os.getenv("EMAIL_PASSWORD", "your-app-password")
        
    async def send_password_reset_email(self, email: str, full_name: str, reset_token: str) -> bool:
        """
        Send password reset email
        """
        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.email_user
            msg['To'] = email
            msg['Subject'] = "Password Reset Request - Expense Management System"
            
            # HTML Email body
            html_body = f"""
            <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hi {full_name},</p>
                
                <p>You requested a password reset for your Expense Management System account.</p>
                
                <div style="background-color: #f0f0f0; padding: 20px; margin: 20px 0; text-align: center;">
                    <h3>Your password reset code is:</h3>
                    <h1 style="color: #007bff; font-size: 36px; letter-spacing: 5px;">{reset_token}</h1>
                </div>
                
                <p><strong>This code will expire in 15 minutes.</strong></p>
                
                <p>If you didn't request this reset, please ignore this email.</p>
                
                <hr>
                <p>Best regards,<br>
                Expense Management System Team</p>
            </body>
            </html>
            """
            
            msg.attach(MimeText(html_body, 'html'))
            
            # Connect to server and send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_user, email, text)
            server.quit()
            
            print(f"✅ Password reset email sent to {email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {email}: {str(e)}")
            return False
    
    async def send_welcome_email(self, email: str, full_name: str, company_name: str) -> bool:
        """
        Send welcome email to new users
        """
        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.email_user
            msg['To'] = email
            msg['Subject'] = f"Welcome to {company_name} - Expense Management System"
            
            html_body = f"""
            <html>
            <body>
                <h2>Welcome to Expense Management System!</h2>
                <p>Hi {full_name},</p>
                
                <p>Your account has been successfully created for <strong>{company_name}</strong>.</p>
                
                <p>You can now:</p>
                <ul>
                    <li>Submit expense claims</li>
                    <li>Track approval status</li>
                    <li>Upload receipts with OCR</li>
                    <li>Manage your team (if you're a manager)</li>
                </ul>
                
                <p>Get started by logging into your account.</p>
                
                <hr>
                <p>Best regards,<br>
                Expense Management System Team</p>
            </body>
            </html>
            """
            
            msg.attach(MimeText(html_body, 'html'))
            
            # Connect to server and send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_user, email, text)
            server.quit()
            
            print(f"✅ Welcome email sent to {email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send welcome email to {email}: {str(e)}")
            return False

# Create instance
email_service = EmailService()