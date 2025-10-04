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
    
    def extract_expense_form_data(self, text: str) -> Dict[str, Any]:
        """Extract specific expense form fields from OCR text"""
        
        # Initialize result dictionary with all form fields
        form_data = {
            "description": None,
            "expense_date": None,
            "category": None,
            "paid_by": None,
            "total_amount": None,
            "currency": None,
            "remarks": None
        }
        
        # Split text into lines for better processing
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text_lower = text.lower()
        
        # Extract Description
        description_patterns = [
            r'description[\s:]*([^\n\r]+)',
            r'desc[\s:]*([^\n\r]+)',
            r'item[\s:]*([^\n\r]+)',
            r'expense[\s:]*([^\n\r]+)'
        ]
        
        for pattern in description_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                form_data["description"] = match.group(1).strip()
                break
        
        # Extract Expense Date
        date_patterns = [
            r'expense\s+date[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'date[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})',
            r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                form_data["expense_date"] = match.group(1).strip()
                break
        
        # Extract Category
        category_patterns = [
            r'category[\s:]*([^\n\r]+)',
            r'cat[\s:]*([^\n\r]+)',
            r'type[\s:]*([^\n\r]+)'
        ]
        
        for pattern in category_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                form_data["category"] = match.group(1).strip()
                break
        
        # If no explicit category found, try to categorize from content
        if not form_data["category"]:
            form_data["category"] = self.categorize_expense(text)
        
        # Extract Paid By
        paid_by_patterns = [
            r'paid\s+by[\s:]*([^\n\r]+)',
            r'paidby[\s:]*([^\n\r]+)',
            r'payment\s+method[\s:]*([^\n\r]+)',
            r'paid[\s:]*([^\n\r]+)'
        ]
        
        for pattern in paid_by_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                paid_by_text = match.group(1).strip()
                # Clean up common payment method indicators
                if any(method in paid_by_text.lower() for method in ['cash', 'card', 'credit', 'debit', 'bank']):
                    form_data["paid_by"] = paid_by_text
                break
        
        # Extract Total Amount and Currency
        amount_patterns = [
            r'total\s+amount[\s:]*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*([a-z]{3})',  # "567 USD"
            r'total\s+amount[\s:]*([a-z]{3})\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # "USD 567"
            r'amount[\s:]*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*([a-z]{3})',  # "567 USD"
            r'amount[\s:]*([a-z]{3})\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # "USD 567"
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*([a-z]{3})',  # Generic "567 USD"
            r'([a-z]{3})\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Generic "USD 567"
            r'[\$£€¥₹]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Symbol-based currencies
            r'(\d+(?:,\d{3})*\.\d{2})'  # Generic decimal number
        ]
        
        # Look for currency indicators
        currency_indicators = {
            '$': 'USD', '£': 'GBP', '€': 'EUR', '¥': 'JPY', '₹': 'INR',
            'usd': 'USD', 'gbp': 'GBP', 'eur': 'EUR', 'jpy': 'JPY', 'inr': 'INR',
            'dollar': 'USD', 'pound': 'GBP', 'euro': 'EUR', 'yen': 'JPY', 'rupee': 'INR'
        }
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    try:
                        if isinstance(match, tuple) and len(match) == 2:
                            first, second = match
                            # Check which one is the number
                            if first.replace(',', '').replace('.', '').isdigit():
                                # First is amount, second is currency
                                form_data["total_amount"] = float(first.replace(',', ''))
                                form_data["currency"] = second.upper()
                            elif second.replace(',', '').replace('.', '').isdigit():
                                # First is currency, second is amount
                                form_data["currency"] = first.upper()
                                form_data["total_amount"] = float(second.replace(',', ''))
                        else:
                            # Single match (just amount)
                            amount_str = match if isinstance(match, str) else str(match)
                            amount_clean = amount_str.replace(',', '').strip()
                            form_data["total_amount"] = float(amount_clean)
                        break
                    except (ValueError, IndexError):
                        continue
                if form_data["total_amount"]:
                    break
        
        # Try to detect currency from symbols in text if not found
        if not form_data["currency"]:
            for symbol, currency in currency_indicators.items():
                if symbol in text_lower:
                    form_data["currency"] = currency
                    break
        
        # Default currency if none detected
        if not form_data["currency"]:
            form_data["currency"] = "USD"  # Default to USD
        
        # Extract Remarks
        remarks_patterns = [
            r'remarks[\s:]*([^\n\r]+)',
            r'notes[\s:]*([^\n\r]+)',
            r'comment[\s:]*([^\n\r]+)',
            r'memo[\s:]*([^\n\r]+)'
        ]
        
        for pattern in remarks_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                form_data["remarks"] = match.group(1).strip()
                break
        
        return form_data
    
    def process_expense_receipt(self, image_path: str) -> Dict[str, Any]:
        """Process expense receipt and extract form-specific data"""
        try:
            # Extract text from image
            text = self.extract_text_from_image(image_path)
            
            if not text:
                return {
                    "success": False,
                    "error": "Could not extract text from image",
                    "confidence": 0.0,
                    "form_data": {}
                }
            
            # Extract form-specific data
            form_data = self.extract_expense_form_data(text)
            
            # Calculate confidence based on extracted fields
            confidence = 0.0
            total_fields = 7  # Total number of form fields
            filled_fields = 0
            
            for field, value in form_data.items():
                if value is not None and str(value).strip():
                    filled_fields += 1
                    if field == "total_amount":
                        confidence += 0.3  # Amount is most important
                    elif field == "expense_date":
                        confidence += 0.2  # Date is second most important
                    elif field == "description":
                        confidence += 0.2  # Description is important
                    else:
                        confidence += 0.1  # Other fields
            
            # Normalize confidence to 0-1 range
            confidence = min(confidence, 1.0)
            
            return {
                "success": True,
                "form_data": form_data,
                "raw_text": text,
                "confidence": confidence,
                "fields_extracted": filled_fields,
                "total_fields": total_fields
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "confidence": 0.0,
                "form_data": {}
            }

ocr_service = OCRService()