# DCP-Planner

A course schedule planning tool that scrapes Liberty University course data and uses constraint programming to generate optimized class schedules.

## Project Overview

DCP-Planner is designed to:
- Scrape course information from Liberty University's course catalog
- Parse course metadata including prerequisites, credits, and offering information
- Generate viable course schedules using constraint programming
- Support both residential and online prerequisite handling

## Project Structure

```
DCP-Planner/
├── Data/
│   ├── DCP Scraping.ipynb          # Jupyter notebook for web scraping course data
│   ├── Offerings_Scrape.py         # Python script to scrape course offerings data 
│   ├── course_cat_urls.csv         # URLs of course category pages
│   ├── Course_Data.csv             # Scraped course data
│   ├── Offerings.csv               # Course offering information 
│   ├── Unique_Code.csv             # Unique course codes
│   └── All_Courses.csv             # Complete course dataset 
│
├── Model/
│   ├── Class.py                    # Course class model with prerequisites and credits
│   ├── Day_Interval.py             # Day and time interval handling
│   ├── Helper.py                   # Utility functions
│   ├── Node.py                     # Graph node representation for constraints
│   ├── Option.py                   # Schedule option representation
│   └── Schedule_Generator.py       # Main constraint programming solver
│
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Dependencies

- **ortools** (9.15.6755) - Google OR-Tools for constraint programming
- **pandas** (2.2.3) - Data manipulation and analysis
- **beautifulsoup4** (4.13.0) - Web scraping HTML parsing
- **requests** (2.31.0) - HTTP library for fetching web pages
- **selenium** (4.11.2) - Automated browser control and actions  
- **webdriver_manager** (3.8.5) - Helper library for selenium

## Setup Instructions

### Prerequisites
- Python 3.x
- Virtual environment (recommended)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd DCP-Planner
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```


### Data Collection
Open `Data/DCP Scraping.ipynb` and run the notebook to:
- Scrape course data from Liberty University catalog
- Parse course information including:
  - Course code and title
  - Credit hours
  - Prerequisites (residential and online)
  - Registration restrictions
  - Offering information
- Generate `Course_Data.csv` with complete course data

Next, open `Data/Offerings_Scrape.py` 
- Navigate to registrar and login
- Scrape course offering data 
- Parse course information including:
  - Course code and title
  - Instructor and location
  - Course availability and time
- Generate `Offerings.csv` with complete offering data

## Key Components

### Class.py
Represents a course with:
- Course code, title, and credits
- Residential and online prerequisites
- Enrollment information
- Integration with OR-Tools constraint model

### Schedule_Generator.py
Implements constraint programming solver to:
- Assign courses to time slots
- Ensure prerequisites are satisfied
- Handle any conflict or constraint


### Day_Interval.py
- Used for conflict detection between course schedules

### Node.py & Option.py
- **Node.py**: Graph representation for prerequisite dependencies
- **Option.py**: Stores and represents valid schedule options


## Notes

- I had to do some manual cleaning on the Offerings.csv and don't quite remember what 🙂
- Have not tested data scraping functionality in a while


## Future Enhancements

- Additional student preference option
- More optimizations to improve performance
- Add visualization of generated schedules
- Ability to optimize for a certain value

## License

MIT License

Copyright (c) 2026 Isaiah Mellace

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Author

Isaiah Mellace