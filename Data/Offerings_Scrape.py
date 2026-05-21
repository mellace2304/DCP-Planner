"""
Liberty University Course Scraper

This script scrapes course data from Liberty University's course registration website.
It iterates through specified semesters and subject codes to collect course information.

Authentication is handled manually by the user.
"""

import csv
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
BASE_URL = "https://course-registration.liberty.edu/{}/search?subjectCode={}"
OUTPUT_FILE = "Offerings.csv"
WAIT_TIME = 10  # seconds to wait for page load

# Read subject codes from CSV
def get_subject_codes(file_path):
    """Read subject codes from CSV file."""
    df = pd.read_csv(file_path)
    return df.iloc[:, 1].tolist()  # Get the second column (index 1)

# Get semester codes to scrape (all Fall and Spring except Spring 2026)
def get_semester_codes():
    """Return semester codes to scrape."""
    # Based on YearSelect.txt, excluding Spring 2026
    # Format: [semester_code, semester_name]
    return [
        ["202540", "Fall 2025"],
        ["202520", "Spring 2025"],
        ["202440", "Fall 2024"],
        ["202420", "Spring 2024"],
        ["202340", "Fall 2023"],
        ["202220", "Spring 2022"]
    ]

# Initialize the WebDriver
def setup_driver():
    print('Setting up Driver')
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    
    # Option 1: Let Selenium find ChromeDriver automatically (if in PATH)
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print('Using system ChromeDriver')
        return driver
    except:
        pass
    
    # Option 2: Specify path to manually downloaded ChromeDriver
    try:
        service = Service("/path/to/your/chromedriver")  # Update this path
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print('Using local ChromeDriver')
        return driver
    except Exception as e:
        print(f"Error setting up driver: {e}")
        return None


# Extract course data from the current page
def extract_course_data(driver, semester_name, subject_code):
    """Extract course data from the current page."""
    courses = []
    
    # Wait for the table to load
    try:
        WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.TAG_NAME, "tbody"))
        )
    except TimeoutException:
        print(f"Timeout waiting for course table to load for {subject_code} in {semester_name}")
        return courses
    
    # Find all course rows
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        
        for row in rows:
            # Extract data from each column
            try:
                course_code = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)").text.strip()
                
                # Title might be in a different column based on viewport size
                try:
                    title = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()
                except:
                    title = "N/A"
                
                # Credits
                try:
                    credits = row.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text.strip()
                except:
                    credits = "N/A"
                
                # Instructor
                try:
                    instructor = row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text.strip()
                except:
                    instructor = "N/A"
                
                # Location
                try:
                    location = row.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text.strip()
                except:
                    location = "N/A"
                # Availability
                try:
                    availability = row.find_element(By.CSS_SELECTOR, "td:nth-child(6)").text.strip()
                except:
                    availability = "N/A"
                
                # Time
                try:
                    time_info = row.find_element(By.CSS_SELECTOR, "td:nth-child(7)").text.strip()
                    if time_info == 'Multiple':
                        row.click()
                        time.sleep(2)
                        meeting_times = driver.find_element(By.CSS_SELECTOR, "#meeting-times-container")
                        children = meeting_times.find_elements(By.XPATH, "./*")
                        time_info = ''
                        for i in range(len(children)):
                            meeting_time = driver.find_element(By.CSS_SELECTOR, f"#meeting-times-container > div:nth-child({i+1}) > div.meeting-right").text.strip()
                            if not time_info:
                                time_info += meeting_time
                            else:
                                time_info += ' and ' + meeting_time
                        time.sleep(1)
                except:
                    time_info = "N/A"
                
                # Notes
                try:
                    notes = row.find_element(By.CSS_SELECTOR, "td:nth-child(8)")
                except:
                    notes = "N/A"
                
                # Add semester and subject code information
                course_data = {
                    "Semester": semester_name,
                    "Subject Code": subject_code,
                    "Course Code": course_code,
                    "Title": title,
                    "Credits": credits,
                    "Instructor": instructor,
                    "Location": location,
                    "Availability": availability,
                    "Time": time_info,
                    "Notes": notes
                }
                
                courses.append(course_data)
                
            except Exception as e:
                print(f"Error extracting data from row: {e}")
                continue
                
    except NoSuchElementException:
        print(f"No course table found for {subject_code} in {semester_name}")
    except Exception as e:
        print(f"Error extracting course data: {e}")
    
    return courses

# Main scraping function
def scrape_courses(subject_codes_file):
    """Main function to scrape courses."""
    subject_codes = get_subject_codes(subject_codes_file)
    semester_codes = get_semester_codes()
    
    driver = setup_driver()
    all_courses = []
    
    try:
        # Pause to allow user to authenticate
        print("Please authenticate in the browser window.")
        print("The script will continue in 30 seconds...")
        time.sleep(40)  # Give user time to log in
        
        # Iterate through each semester and subject code
        for semester_code, semester_name in semester_codes:
            print(f"Processing semester: {semester_name}")
            
            for subject_code in subject_codes:
                print(f"  Processing subject: {subject_code}")
                
                # Navigate to the course page
                url = BASE_URL.format(semester_code, subject_code)
                driver.get(url) # type: ignore
                
                # Wait for page to load
                time.sleep(WAIT_TIME)
                
                # Extract course data
                courses = extract_course_data(driver, semester_name, subject_code)
                all_courses.extend(courses)
                
                print(f"    Found {len(courses)} courses")
                
                # Small delay between requests to avoid overloading the server
                time.sleep(5)
    
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Save data to CSV
        if all_courses:
            save_to_csv(all_courses, OUTPUT_FILE)
            print(f"Data saved to {OUTPUT_FILE}")
        
        # Close the browser
        driver.quit() # type: ignore

# Save data to CSV
def save_to_csv(courses, output_file):
    """Save course data to CSV file."""
    if not courses:
        print("No courses to save.")
        return
    
    # Get all unique keys to ensure all columns are included
    fieldnames = set()
    for course in courses:
        fieldnames.update(course.keys())
    
    fieldnames = sorted(list(fieldnames))
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(courses)

if __name__ == "__main__":
    subject_codes_file = "Unique_Code.csv"
    scrape_courses(subject_codes_file)
