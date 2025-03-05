#!/usr/bin/env python3
"""
Script to convert an HTML file to PDF using WeasyPrint with graceful page break handling
"""
import os
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def convert_html_to_pdf(html_file, pdf_file):
    """
    Convert HTML file to PDF using WeasyPrint with page break optimization
    
    Args:
        html_file (str): Path to the HTML file
        pdf_file (str): Path to save the PDF file
    """
    try:
        # Check if HTML file exists
        if not os.path.exists(html_file):
            print(f"Error: HTML file '{html_file}' not found!")
            return False
        
        # Configure fonts
        font_config = FontConfiguration()
        
        # CSS for better page break handling
        page_break_css = CSS(string='''
            /* General page settings */
            @page {
                margin: 1cm;
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                }
            }
            
            /* Keep headings with their content */
            h1, h2, h3, h4, h5, h6 {
                page-break-after: avoid;
            }
            
            /* Keep paragraphs together where possible */
            p {
                orphans: 3;
                widows: 3;
            }
            
            /* Prevent breaks inside property information blocks */
            .property-item {
                page-break-inside: avoid;
            }
            
            /* Add page breaks before new major sections if needed */
            .section-break {
                page-break-before: always;
            }
            
            /* Ensure tables don't break mid-row if possible */
            tr, td, th {
                page-break-inside: avoid;
            }
            
            /* Handle images and media */
            img, video {
                max-width: 100%;
                height: auto;
            }
        ''')
        
        # Convert HTML to PDF with page break CSS
        print(f"Converting '{html_file}' to PDF with optimized page breaks...")
        HTML(html_file).write_pdf(
            pdf_file, 
            stylesheets=[page_break_css], 
            font_config=font_config
        )
        
        # Check if PDF was created successfully
        if os.path.exists(pdf_file):
            print(f"PDF created successfully: '{pdf_file}'")
            return True
        else:
            print(f"Error: Failed to create PDF file '{pdf_file}'!")
            return False
    
    except Exception as e:
        print(f"Error converting HTML to PDF: {str(e)}")
        return False

if __name__ == "__main__":
    # Define input and output file paths
    html_file = "tour_schedule_350_5th_Ave,_New_York,_NY_10118_20250304022942.html"
    pdf_file = "tour_schedule.pdf"
    
    # Convert HTML to PDF with page break handling
    convert_html_to_pdf(html_file, pdf_file)

