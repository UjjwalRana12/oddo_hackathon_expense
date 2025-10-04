import pytesseract
import cv2
import numpy as np
from PIL import Image
import re
from datetime import datetime
from typing import Dict, Optional, Any
import os

class OCRService:
    """Service for OCR processing of receipts"""
    
    def __init__(self):
        # Configure tesseract path if needed (Windows)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR results"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Could not load image")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply threshold to get binary image
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Remove noise
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            cleaned = cv2.medianBlur(cleaned, 3)
            
            return cleaned
            
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            # Return original image if preprocessing fails
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            
            # Use pytesseract to extract text
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            return text.strip()
            
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""
    
    def extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amount from text"""
        # Common currency symbols and patterns
        currency_patterns = [
            r'[\$£€¥₹]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $123.45, £1,234.56
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*[\$£€¥₹]',  # 123.45$
            r'(?:total|amount|sum|price|cost)[\s:]*[\$£€¥₹]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Total: $123.45
            r'(\d+(?:,\d{3})*\.\d{2})'  # Generic decimal number
        ]
        
        for pattern in currency_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Get the largest amount (likely the total)
                amounts = []
                for match in matches:
                    try:
                        # Remove commas and convert to float
                        amount_str = match.replace(',', '')
                        amount = float(amount_str)
                        amounts.append(amount)
                    except ValueError:
                        continue
                
                if amounts:
                    return max(amounts)
        
        return None
    
    def extract_date(self, text: str) -> Optional[str]:
        """Extract date from text"""
        date_patterns = [
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',  # MM/DD/YYYY, DD/MM/YYYY
            r'(\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',  # YYYY/MM/DD
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',  # DD Month YYYY
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})'  # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    def extract_merchant_name(self, text: str) -> Optional[str]:
        """Extract merchant/restaurant name from text"""
        lines = text.split('\n')
        # Usually the merchant name is at the top of the receipt
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if len(line) > 3 and not re.match(r'^\d+[\s\d\-\/\.]*$', line):  # Not just numbers/dates
                # Remove common receipt terms
                cleaned_line = re.sub(r'(?i)(receipt|bill|invoice|tax|gst|vat)', '', line).strip()
                if len(cleaned_line) > 3:
                    return cleaned_line
        
        return None
    
    def categorize_expense(self, text: str, merchant_name: Optional[str] = None) -> Optional[str]:
        """Categorize expense based on text content"""
        text_lower = text.lower()
        
        # Food & Dining
        food_keywords = ['restaurant', 'cafe', 'coffee', 'food', 'dining', 'meal', 'lunch', 'dinner', 'breakfast']
        if any(keyword in text_lower for keyword in food_keywords):
            return "Food & Dining"
        
        # Transportation
        transport_keywords = ['taxi', 'uber', 'lyft', 'bus', 'train', 'flight', 'airline', 'parking', 'fuel', 'gas']
        if any(keyword in text_lower for keyword in transport_keywords):
            return "Transportation"
        
        # Office Supplies
        office_keywords = ['office', 'supplies', 'stationery', 'paper', 'pen', 'printer']
        if any(keyword in text_lower for keyword in office_keywords):
            return "Office Supplies"
        
        # Accommodation
        hotel_keywords = ['hotel', 'motel', 'accommodation', 'lodging', 'stay']
        if any(keyword in text_lower for keyword in hotel_keywords):
            return "Accommodation"
        
        return "Other"
    
    def process_receipt(self, image_path: str) -> Dict[str, Any]:
        """Process receipt image and extract structured data"""
        try:
            # Extract text
            text = self.extract_text_from_image(image_path)
            
            if not text:
                return {
                    "success": False,
                    "error": "Could not extract text from image",
                    "confidence": 0.0
                }
            
            # Extract information
            amount = self.extract_amount(text)
            date = self.extract_date(text)
            merchant_name = self.extract_merchant_name(text)
            category = self.categorize_expense(text, merchant_name)
            
            # Calculate confidence based on extracted data
            confidence = 0.0
            if amount is not None:
                confidence += 0.4
            if date is not None:
                confidence += 0.3
            if merchant_name is not None:
                confidence += 0.2
            if category != "Other":
                confidence += 0.1
            
            return {
                "success": True,
                "amount": amount,
                "date": date,
                "merchant_name": merchant_name,
                "category": category,
                "description": merchant_name or "Expense",
                "raw_text": text,
                "confidence": confidence
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "confidence": 0.0
            }

ocr_service = OCRService()