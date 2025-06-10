import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Any
import io
import zipfile

# Configure Streamlit page
st.set_page_config(
    page_title="GST-Based Business Assessment System",
    page_icon="📊",
    layout="wide"
)

class GSTDataAnalyzer:
    def __init__(self):
        self.monthly_data = {}
        self.analysis_results = {}
        
    def parse_b2b_file(self, file_content: str) -> pd.DataFrame:
        """Parse B2B sales file"""
        try:
            df = pd.read_csv(io.StringIO(file_content))
            # Clean column names
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"Error parsing B2B file: {str(e)}")
            return pd.DataFrame()
    
    def parse_b2c_file(self, file_content: str) -> pd.DataFrame:
        """Parse B2C sales file"""
        try:
            df = pd.read_csv(io.StringIO(file_content))
            # Clean column names  
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"Error parsing B2C file: {str(e)}")
            return pd.DataFrame()
            
    def parse_purchase_file(self, file_content: str) -> pd.DataFrame:
        """Parse purchase/GSTR2B file"""
        try:
            # Handle both CSV and Excel files
            if file_content.startswith('GSTIN'):
                df = pd.read_csv(io.StringIO(file_content))
            else:
                # For Excel files, read as binary and parse
                df = pd.read_excel(io.BytesIO(file_content.encode('latin1')))
            return df
        except Exception as e:
            st.warning(f"Could not parse purchase file: {str(e)}")
            return pd.DataFrame()
    
    def analyze_monthly_data(self, month_name: str, b2b_df: pd.DataFrame, 
                           b2c_df: pd.DataFrame, purchase_df: pd.DataFrame) -> Dict:
        """Analyze GST data for a single month"""
        
        analysis = {
            'month': month_name,
            'b2b_transactions': len(b2b_df),
            'b2c_transactions': len(b2c_df),
            'purchase_transactions': len(purchase_df),
            'b2b_sales': 0,
            'b2c_sales': 0,
            'total_sales': 0,
            'total_purchases': 0,
            'gst_collected': 0,
            'gst_paid': 0,
            'tax_rates_used': [],
            'interstate_sales': 0,
            'intrastate_sales': 0,
            'unique_customers': 0
        }
        
        # Analyze B2B sales
        if not b2b_df.empty:
            b2b_sales = b2b_df['Invoice Value'].fillna(0).sum()
            analysis['b2b_sales'] = b2b_sales
            
            # GST collected from B2B
            if 'Taxable Value' in b2b_df.columns and 'Rate' in b2b_df.columns:
                gst_from_b2b = (b2b_df['Taxable Value'].fillna(0) * 
                               b2b_df['Rate'].fillna(0) / 100).sum()
                analysis['gst_collected'] += gst_from_b2b
            
            # Unique customers
            if 'GSTIN/UIN of Recipient' in b2b_df.columns:
                analysis['unique_customers'] = b2b_df['GSTIN/UIN of Recipient'].nunique()
            
            # Tax rates used
            if 'Rate' in b2b_df.columns:
                rates = b2b_df['Rate'].dropna().unique()
                analysis['tax_rates_used'].extend(rates)
        
        # Analyze B2C sales
        if not b2c_df.empty:
            b2c_sales = b2c_df['Taxable Value'].fillna(0).sum()
            analysis['b2c_sales'] = b2c_sales
            
            # GST collected from B2C
            if 'Rate' in b2c_df.columns:
                gst_from_b2c = (b2c_df['Taxable Value'].fillna(0) * 
                               b2c_df['Rate'].fillna(0) / 100).sum()
                analysis['gst_collected'] += gst_from_b2c
                
                # Tax rates used
                rates = b2c_df['Rate'].dropna().unique()
                analysis['tax_rates_used'].extend(rates)
        
        # Total sales
        analysis['total_sales'] = analysis['b2b_sales'] + analysis['b2c_sales']
        
        # Remove duplicates from tax rates
        analysis['tax_rates_used'] = list(set(analysis['tax_rates_used']))
        
        # Analyze purchases (if available)
        if not purchase_df.empty:
            # This is a simplified analysis - actual GSTR2B has complex structure
            if 'Taxable Value' in purchase_df.columns:
                analysis['total_purchases'] = purchase_df['Taxable Value'].fillna(0).sum()
            elif 'Invoice Value' in purchase_df.columns:
                analysis['total_purchases'] = purchase_df['Invoice Value'].fillna(0).sum()
        
        return analysis
    
    def calculate_aggregate_metrics(self, monthly_analyses: List[Dict]) -> Dict:
        """Calculate aggregate business metrics from monthly data"""
        
        if not monthly_analyses:
            return {}
        
        # Sum up all monthly data
        total_sales = sum(m['total_sales'] for m in monthly_analyses)
        total_purchases = sum(m['total_purchases'] for m in monthly_analyses)
        total_gst_collected = sum(m['gst_collected'] for m in monthly_analyses)
        avg_monthly_sales = total_sales / len(monthly_analyses)
        
        # Estimate annual figures
        months_of_data = len(monthly_analyses)
        annual_turnover = (total_sales / months_of_data) * 12
        
        # Calculate ratios
        b2b_total = sum(m['b2b_sales'] for m in monthly_analyses)
        b2c_total = sum(m['b2c_sales'] for m in monthly_analyses)
        
        b2b_percentage = (b2b_total / total_sales * 100) if total_sales > 0 else 0
        
        # Business patterns
        avg_transactions_per_month = sum(
            m['b2b_transactions'] + m['b2c_transactions'] 
            for m in monthly_analyses
        ) / len(monthly_analyses)
        
        # Compliance indicators
        filing_frequency = len(monthly_analyses)  # Number of months with data
        
        # Tax compliance - check if using standard GST rates
        all_rates = []
        for m in monthly_analyses:
            all_rates.extend(m['tax_rates_used'])
        
        standard_rates = [0, 5, 12, 18, 28]
        uses_standard_rates = all(rate in standard_rates for rate in set(all_rates))
        
        return {
            'annual_turnover': annual_turnover,
            'total_sales': total_sales,
            'total_purchases': total_purchases,
            'avg_monthly_sales': avg_monthly_sales,
            'total_gst_collected': total_gst_collected,
            'b2b_percentage': b2b_percentage,
            'b2c_percentage': 100 - b2b_percentage,
            'filing_frequency': filing_frequency,
            'avg_transactions_per_month': avg_transactions_per_month,
            'uses_standard_rates': uses_standard_rates,
            'profit_margin_estimate': max(5, min(25, (total_sales - total_purchases) / total_sales * 100)) if total_sales > 0 else 10,
            'gst_compliance_score': min(100, filing_frequency * 15 + (50 if uses_standard_rates else 0))
        }

class BusinessEligibilityEngine:
    def __init__(self):
        self.schemes = {
            "advance_authorisation": {
                "name": "Advance Authorisation Scheme (Export Incentive)",
                "url": "https://www.dgft.gov.in/advance-authorisation"
            },
            "epcg": {
                "name": "Export Promotion Capital Goods (EPCG) Scheme", 
                "url": "https://www.dgft.gov.in/epcg"
            },
            "startup_tax_benefits": {
                "name": "Startup Tax Benefits",
                "url": "https://startupindia.gov.in/"
            },
            "pmmy_loans": {
                "name": "MSME Loans under PMMY",
                "url": "https://www.mudra.org.in/"
            },
            "nsic_support": {
                "name": "NSIC Marketing & Credit Support",
                "url": "https://www.nsic.co.in/"
            },
            "digital_lending": {
                "name": "Digital Lending Using GST Data",
                "url": "Partner with NBFCs or Fintech platforms"
            },
            "gem_platform": {
                "name": "Government e-Marketplace (GeM)",
                "url": "https://gem.gov.in/"
            },
            "income_tax_deduction": {
                "name": "Income Tax Profit Deduction for Startups",
                "url": "Claim deduction in Income Tax Return (ITR) filing"
            },
            "gst_composition": {
                "name": "GST Composition Scheme",
                "url": "Opt-in via GST portal during registration or return filing"
            }
        }

    def assess_scheme_eligibility(self, business_data: Dict, gst_metrics: Dict) -> Dict[str, Dict]:
        """Assess eligibility for all schemes based on business and GST data"""
        results = {}
        
        # Extract key metrics
        annual_turnover = gst_metrics.get('annual_turnover', 0)
        gst_compliance_score = gst_metrics.get('gst_compliance_score', 0)
        filing_frequency = gst_metrics.get('filing_frequency', 0)
        
        # Advance Authorisation Scheme
        if business_data.get('business_type') == 'exporter':
            results['advance_authorisation'] = {
                'eligible': True,
                'reason': "Eligible as registered exporter with GST data",
                'scheme_name': self.schemes['advance_authorisation']['name'],
                'url': self.schemes['advance_authorisation']['url']
            }
        else:
            results['advance_authorisation'] = {
                'eligible': False,
                'reason': "Only available for exporters",
                'scheme_name': self.schemes['advance_authorisation']['name'],
                'url': self.schemes['advance_authorisation']['url']
            }
        
        # PMMY Loans
        if business_data.get('business_type') in ['msme', 'manufacturer', 'trader']:
            loan_category = "Shishu" if annual_turnover < 1000000 else "Kishore" if annual_turnover < 5000000 else "Tarun"
            results['pmmy_loans'] = {
                'eligible': True,
                'reason': f"Eligible for PMMY {loan_category} loan based on turnover",
                'scheme_name': self.schemes['pmmy_loans']['name'],
                'url': self.schemes['pmmy_loans']['url']
            }
        else:
            results['pmmy_loans'] = {
                'eligible': False,
                'reason': "Must be MSME/manufacturer/trader",
                'scheme_name': self.schemes['pmmy_loans']['name'],
                'url': self.schemes['pmmy_loans']['url']
            }
        
        # Startup Benefits
        if business_data.get('business_type') == 'startup':
            incorporation_date = pd.to_datetime(business_data.get('incorporation_date'))
            min_date = pd.to_datetime('2016-04-01')
            
            if incorporation_date >= min_date and annual_turnover < 1000000000:
                results['startup_tax_benefits'] = {
                    'eligible': True,
                    'reason': "Eligible startup with turnover < 100 Cr",
                    'scheme_name': self.schemes['startup_tax_benefits']['name'],
                    'url': self.schemes['startup_tax_benefits']['url']
                }
            else:
                results['startup_tax_benefits'] = {
                    'eligible': False,
                    'reason': "Must be incorporated after Apr 2016 with turnover < 100 Cr",
                    'scheme_name': self.schemes['startup_tax_benefits']['name'],
                    'url': self.schemes['startup_tax_benefits']['url']
                }
        else:
            results['startup_tax_benefits'] = {
                'eligible': False,
                'reason': "Only for registered startups",
                'scheme_name': self.schemes['startup_tax_benefits']['name'],
                'url': self.schemes['startup_tax_benefits']['url']
            }
        
        # Digital Lending
        if gst_compliance_score > 60 and annual_turnover > 500000:
            results['digital_lending'] = {
                'eligible': True,
                'reason': "Good GST compliance with sufficient turnover",
                'scheme_name': self.schemes['digital_lending']['name'],
                'url': self.schemes['digital_lending']['url']
            }
        else:
            results['digital_lending'] = {
                'eligible': False,
                'reason': "Need better GST compliance and minimum turnover",
                'scheme_name': self.schemes['digital_lending']['name'],
                'url': self.schemes['digital_lending']['url']
            }
        
        # GeM Platform
        if filing_frequency >= 3:  # At least 3 months of data
            results['gem_platform'] = {
                'eligible': True,
                'reason': "Regular GST filing history available",
                'scheme_name': self.schemes['gem_platform']['name'],
                'url': self.schemes['gem_platform']['url']
            }
        else:
            results['gem_platform'] = {
                'eligible': False,
                'reason': "Need consistent GST filing history",
                'scheme_name': self.schemes['gem_platform']['name'],
                'url': self.schemes['gem_platform']['url']
            }
        
        # GST Composition Scheme
        state = business_data.get('state', '').lower()
        ne_hill_states = ['arunachal pradesh', 'assam', 'manipur', 'meghalaya', 'mizoram', 
                         'nagaland', 'sikkim', 'tripura', 'himachal pradesh', 'uttarakhand']
        
        threshold = 7500000 if any(ne_state in state for ne_state in ne_hill_states) else 15000000
        
        if (annual_turnover < threshold and 
            business_data.get('business_type') in ['manufacturer', 'trader', 'restaurant']):
            results['gst_composition'] = {
                'eligible': True,
                'reason': f"Turnover below threshold (₹{threshold:,})",
                'scheme_name': self.schemes['gst_composition']['name'],
                'url': self.schemes['gst_composition']['url']
            }
        else:
            results['gst_composition'] = {
                'eligible': False,
                'reason': f"Turnover exceeds threshold or ineligible business type",
                'scheme_name': self.schemes['gst_composition']['name'],
                'url': self.schemes['gst_composition']['url']
            }
        
        return results

class LoanAssessmentEngine:
    def __init__(self):
        self.base_interest_rates = {
            'excellent': 9.0,
            'good': 11.5,
            'fair': 14.0,
            'poor': 17.5
        }
    
    def calculate_credit_score(self, business_data: Dict, gst_metrics: Dict) -> Tuple[int, str]:
        """Calculate credit score based on business and GST metrics"""
        score = 300  # Base score
        
        # GST compliance (0-200 points)
        gst_compliance = gst_metrics.get('gst_compliance_score', 0)
        score += min(200, gst_compliance * 2)
        
        # Business turnover (0-200 points)
        annual_turnover = gst_metrics.get('annual_turnover', 0)
        if annual_turnover > 50000000:  # > 5 Cr
            score += 200
        elif annual_turnover > 10000000:  # > 1 Cr
            score += 150
        elif annual_turnover > 5000000:   # > 50 L
            score += 100
        elif annual_turnover > 1000000:   # > 10 L
            score += 75
        elif annual_turnover > 500000:    # > 5 L
            score += 50
        
        # Filing consistency (0-100 points)
        filing_frequency = gst_metrics.get('filing_frequency', 0)
        if filing_frequency >= 12:
            score += 100
        elif filing_frequency >= 6:
            score += 75
        elif filing_frequency >= 3:
            score += 50
        elif filing_frequency >= 1:
            score += 25
        
        # Business vintage (0-100 points)
        try:
            incorporation_date = pd.to_datetime(business_data.get('incorporation_date'))
            years_in_business = (datetime.now() - incorporation_date).days / 365.25
            if years_in_business > 5:
                score += 100
            elif years_in_business > 3:
                score += 75
            elif years_in_business > 1:
                score += 50
            elif years_in_business > 0.5:
                score += 25
        except:
            score += 25  # Default if date parsing fails
        
        # Business model stability (0-100 points)
        b2b_percentage = gst_metrics.get('b2b_percentage', 0)
        if b2b_percentage > 70:
            score += 100  # B2B businesses are considered more stable
        elif b2b_percentage > 40:
            score += 75
        elif b2b_percentage > 10:
            score += 50
        else:
            score += 25   # B2C businesses have different risk profile
        
        # Cap the score
        score = min(score, 900)
        
        # Determine credit grade
        if score >= 750:
            grade = 'excellent'
        elif score >= 650:
            grade = 'good'
        elif score >= 500:
            grade = 'fair'
        else:
            grade = 'poor'
            
        return score, grade
    
    def calculate_loan_eligibility(self, business_data: Dict, gst_metrics: Dict) -> Dict:
        """Calculate comprehensive loan assessment"""
        credit_score, credit_grade = self.calculate_credit_score(business_data, gst_metrics)
        
        annual_turnover = gst_metrics.get('annual_turnover', 0)
        profit_margin = gst_metrics.get('profit_margin_estimate', 10)
        
        # Calculate maximum loan amount (15-30% of annual turnover based on credit grade)
        loan_multipliers = {
            'excellent': 0.30,
            'good': 0.25,
            'fair': 0.20,
            'poor': 0.15
        }
        
        max_loan_amount = annual_turnover * loan_multipliers[credit_grade]
        
        # Adjust for business type
        business_type = business_data.get('business_type', '')
        if business_type == 'startup':
            max_loan_amount *= 0.8  # Reduce for higher risk
        elif business_type == 'exporter':
            max_loan_amount *= 1.2  # Increase for export businesses
        
        # Interest rate calculation
        base_rate = self.base_interest_rates[credit_grade]
        
        # Adjustments based on various factors
        if business_type == 'startup':
            base_rate += 1.5
        elif business_type == 'exporter':
            base_rate -= 0.5
        
        if profit_margin > 20:
            base_rate -= 0.5
        elif profit_margin < 5:
            base_rate += 1.0
        
        # GST compliance adjustment
        gst_compliance = gst_metrics.get('gst_compliance_score', 0)
        if gst_compliance > 80:
            base_rate -= 0.5
        elif gst_compliance < 50:
            base_rate += 1.0
        
        final_interest_rate = max(base_rate, 8.5)  # Minimum rate cap
        
        # Loan tenure
        if credit_score > 700:
            max_tenure_years = 7
        elif credit_score > 600:
            max_tenure_years = 5
        else:
            max_tenure_years = 3
        
        # Default loan amount (smaller of max or 10L)
        recommended_amount = min(max_loan_amount, 1000000)
        
        # EMI calculation
        monthly_rate = final_interest_rate / (12 * 100)
        tenure_months = max_tenure_years * 12
        
        if monthly_rate > 0:
            emi = recommended_amount * monthly_rate * (1 + monthly_rate)**tenure_months / ((1 + monthly_rate)**tenure_months - 1)
        else:
            emi = recommended_amount / tenure_months
        
        # Approval probability
        approval_factors = [
            min(30, credit_score / 25),  # Credit score factor (max 30)
            min(25, gst_compliance / 4), # GST compliance factor (max 25)
            min(20, annual_turnover / 250000), # Turnover factor (max 20)
            min(15, profit_margin),      # Profit margin factor (max 15)
            10 if gst_metrics.get('filing_frequency', 0) >= 6 else 5  # Filing consistency (10 or 5)
        ]
        
        approval_probability = min(95, sum(approval_factors))
        
        return {
            'credit_score': credit_score,
            'credit_grade': credit_grade,
            'max_loan_amount': max_loan_amount,
            'recommended_amount': recommended_amount,
            'interest_rate': final_interest_rate,
            'max_tenure_years': max_tenure_years,
            'monthly_emi': emi,
            'total_interest': (emi * tenure_months) - recommended_amount,
            'approval_probability': approval_probability,
            'annual_turnover': annual_turnover,
            'profit_margin': profit_margin
        }

def main():
    st.title("📊 GST-Based Business Assessment System")
    st.markdown("### Analyze your GST data for loan eligibility and government scheme benefits")
    
    # Sidebar
    st.sidebar.title("📋 Instructions")
    st.sidebar.markdown("""
    **What you need:**
    1. Basic business information
    2. GST sales files (B2B & B2C) 
    3. GST purchase files (optional)
    
    **Recommended:** Upload 6 months of GST data for accurate assessment
    
    **File formats accepted:**
    - CSV files from GST portal
    - Excel files (GSTR2B)
    """)
    
    # Initialize session state
    if 'business_data' not in st.session_state:
        st.session_state.business_data = {}
    if 'gst_files' not in st.session_state:
        st.session_state.gst_files = {}
    
    # Step 1: Business Information
    st.header("🏢 Step 1: Business Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        gstin = st.text_input("GSTIN", placeholder="22AAAAA0000A1Z5", help="15-digit GST Identification Number")
        business_name = st.text_input("Business Name", placeholder="ABC Enterprises Pvt Ltd")
        business_type = st.selectbox("Business Type", 
                                   ['msme', 'exporter', 'startup', 'manufacturer', 'trader', 'restaurant'],
                                   help="Select your primary business category")
    
    with col2:
        business_category = st.selectbox("Business Category", ['goods', 'services', 'both'])
        incorporation_date = st.date_input("Incorporation Date", 
                                         value=datetime(2020, 1, 1),
                                         min_value=datetime(1950, 1, 1),
                                         max_value=datetime.now())
        state = st.text_input("State", placeholder="Gujarat, Karnataka, etc.")
    
    # Store business data
    st.session_state.business_data = {
        'gstin': gstin,
        'business_name': business_name,
        'business_type': business_type,
        'business_category': business_category,
        'incorporation_date': incorporation_date.strftime('%Y-%m-%d'),
        'state': state
    }
    
    # Step 2: GST Data Upload
    st.header("📤 Step 2: Upload GST Data Files")
    st.info("💡 Upload files for multiple months to get more accurate assessment. Minimum 1 month required.")
    
    # File upload section
    uploaded_files = st.file_uploader(
        "Upload GST Files (B2B sales, B2C sales, Purchase data)",
        type=['csv', 'xlsx'],
        accept_multiple_files=True,
        help="Upload B2B and B2C sales files, and optionally purchase/GSTR2B files"
    )
    
    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} files uploaded")
        
        # Categorize files
        b2b_files = []
        b2c_files = []
        purchase_files = []
        
        for file in uploaded_files:
            file_name = file.name.lower()
            if 'b2b' in file_name:
                b2b_files.append(file)
            elif 'b2c' in file_name:
                b2c_files.append(file)
            else:
                purchase_files.append(file)
        
        st.write(f"📊 Categorized files: {len(b2b_files)} B2B, {len(b2c_files)} B2C, {len(purchase_files)} Purchase")
        
        # Process files
        if st.button("🔍 Analyze GST Data", type="primary"):
            if not (b2b_files or b2c_files):
                st.error("❌ Please upload at least one B2B or B2C sales file")
                return
            
            analyzer = GSTDataAnalyzer()
            monthly_analyses = []
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Process all combinations of files
            max_files = max(len(b2b_files), len(b2c_files))
            
            for i in range(max_files):
                status_text.text(f'Processing month {i+1}...')
                progress_bar.progress((i + 1) / max_files)
                
                # Get files for this month
                b2b_file = b2b_files[i] if i < len(b2b_files) else None
                b2c_file = b2c_files[i] if i < len(b2c_files) else None
                purchase_file = purchase_files[i] if i < len(purchase_files) else None
                
                # Parse files
                b2b_df = pd.DataFrame()
                b2c_df = pd.DataFrame()
                purchase_df = pd.DataFrame()
                
                if b2b_file:
                    b2b_content = b2b_file.read().decode('utf-8')
                    b2b_df = analyzer.parse_b2b_file(b2b_content)
                
                if b2c_file:
                    b2c_content = b2c_file.read().decode('utf-8')
                    b2c_df = analyzer.parse_b2c_file(b2c_content)
                
                if purchase_file:
                    try:
                        if purchase_file.name.endswith('.csv'):
                            purchase_content = purchase_file.read().decode('utf-8')
                            purchase_df = analyzer.parse_purchase_file(purchase_content)
                        else:
                            # Handle Excel files
                            purchase_df = pd.read_excel(purchase_file)
                    except Exception as e:
                        st.warning(f"Could not process purchase file {purchase_file.name}: {str(e)}")
                
                # Analyze this month's data
                month_name = f"Month {i+1}"
                if b2b_file:
                    month_name += f" ({b2b_file.name.split('_')[0] if '_' in b2b_file.name else 'B2B'})"
                elif b2c_file:
                    month_name += f" ({b2c_file.name.split('_')[0] if '_' in b2c_file.name else 'B2C'})"
                
                month_analysis = analyzer.analyze_monthly_data(month_name, b2b_df, b2c_df, purchase_df)
                monthly_analyses.append(month_analysis)
            
            progress_bar.empty()
            status_text.empty()
            
            # Calculate aggregate metrics
            gst_metrics = analyzer.calculate_aggregate_metrics(monthly_analyses)
            
            if not gst_metrics:
                st.error("❌ Could not analyze GST data. Please check file format.")
                return
            
            # Display analysis results
            st.header("📊 GST Data Analysis Results")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Annual Turnover", f"₹{gst_metrics['annual_turnover']:,.0f}")
            with col2:
                st.metric("Months of Data", len(monthly_analyses))
            with col3:
                st.metric("GST Compliance", f"{gst_metrics['gst_compliance_score']:.0f}/100")
            with col4:
                st.metric("B2B vs B2C", f"{gst_metrics['b2b_percentage']:.1f}% : {gst_metrics['b2c_percentage']:.1f}%")
            
            # Monthly breakdown
            with st.expander("📅 Monthly Breakdown"):
                monthly_df = pd.DataFrame(monthly_analyses)
                if not monthly_df.empty:
                    st.dataframe(monthly_df[['month', 'total_sales', 'b2b_sales', 'b2c_sales', 'gst_collected']])
            
            # Step 3: Assessment Results
            st.header("🎯 Assessment Results")
            
            # Initialize engines
            eligibility_engine = BusinessEligibilityEngine()
            loan_engine = LoanAssessmentEngine()
            
            # Get assessments
            scheme_results = eligibility_engine.assess_scheme_eligibility(
                st.session_state.business_data, gst_metrics)
            loan_results = loan_engine.calculate_loan_eligibility(
                st.session_state.business_data, gst_metrics)
            
            # Display results in two columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🏛️ Government Scheme Eligibility")
                
                eligible_count = sum(1 for scheme in scheme_results.values() if scheme['eligible'])
                st.info(f"**Eligible for {eligible_count} out of {len(scheme_results)} schemes**")
                
                for scheme_key, scheme in scheme_results.items():
                    if scheme['eligible']:
                        st.success(f"✅ **{scheme['scheme_name']}**")
                        st.caption(f"🔗 {scheme['url']}")
                    else:
                        with st.expander(f"❌ {scheme['scheme_name']}"):
                            st.write(scheme['reason'])
                            st.caption(f"🔗 {scheme['url']}")
            
            with col2:
                st.subheader("💰 Loan Assessment")
                
                # Credit score visualization
                score = loan_results['credit_score']
                if score >= 750:
                    score_color = "🟢"
                    score_status = "Excellent"
                elif score >= 650:
                    score_color = "🟡" 
                    score_status = "Good"
                elif score >= 500:
                    score_color = "🟠"
                    score_status = "Fair"
                else:
                    score_color = "🔴"
                    score_status = "Needs Improvement"
                
                st.metric("Credit Score", f"{score_color} {score}", f"Grade: {score_status}")
                
                # Loan details
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Max Loan Amount", f"₹{loan_results['max_loan_amount']:,.0f}")
                    st.metric("Interest Rate", f"{loan_results['interest_rate']:.2f}%")
                
                with col_b:
                    st.metric("Approval Probability", f"{loan_results['approval_probability']:.1f}%")
                    st.metric("Max Tenure", f"{loan_results['max_tenure_years']} years")
                
                # EMI Calculator
                st.markdown("**Loan Calculator:**")
                requested_amount = st.slider(
                    "Loan Amount", 
                    min_value=100000, 
                    max_value=int(loan_results['max_loan_amount']),
                    value=min(1000000, int(loan_results['max_loan_amount'])),
                    step=50000,
                    format="₹%d"
                )
                
                # Recalculate EMI for requested amount
                monthly_rate = loan_results['interest_rate'] / (12 * 100)
                tenure_months = loan_results['max_tenure_years'] * 12
                
                if monthly_rate > 0:
                    emi = requested_amount * monthly_rate * (1 + monthly_rate)**tenure_months / ((1 + monthly_rate)**tenure_months - 1)
                else:
                    emi = requested_amount / tenure_months
                
                st.write(f"**Monthly EMI:** ₹{emi:,.0f}")
                st.write(f"**Total Interest:** ₹{(emi * tenure_months) - requested_amount:,.0f}")
                st.write(f"**Total Amount:** ₹{emi * tenure_months:,.0f}")
            
            # Summary and recommendations
            st.header("📋 Summary & Recommendations")
            
            # Strengths
            strengths = []
            if gst_metrics['gst_compliance_score'] > 70:
                strengths.append("Strong GST compliance record")
            if gst_metrics['annual_turnover'] > 5000000:
                strengths.append("Healthy annual turnover")
            if gst_metrics['filing_frequency'] >= 6:
                strengths.append("Consistent GST filing history")
            if loan_results['credit_score'] > 650:
                strengths.append("Good creditworthiness profile")
            
            # Areas for improvement
            improvements = []
            if gst_metrics['gst_compliance_score'] < 60:
                improvements.append("Improve GST filing consistency")
            if loan_results['credit_score'] < 600:
                improvements.append("Build stronger credit history")
            if gst_metrics['filing_frequency'] < 6:
                improvements.append("Maintain regular GST filings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.success("**Strengths:**")
                for strength in strengths:
                    st.write(f"• {strength}")
            
            with col2:
                if improvements:
                    st.warning("**Areas for Improvement:**")
                    for improvement in improvements:
                        st.write(f"• {improvement}")
                else:
                    st.success("**Excellent Profile!**")
                    st.write("Your business shows strong financial health across all metrics.")

if __name__ == "__main__":
    main()