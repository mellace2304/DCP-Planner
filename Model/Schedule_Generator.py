from ortools.sat.python import cp_model
import pandas as pd
import re
from Helper import *
from Class import Class
from Day_Interval import Day_Interval
from Option import Option
from Node import Node

            



def apply_constraint(model:cp_model.CpModel, variable, operation:str, value:int, enforcer): 
    #Helper function for applying custom constraints
    """Applies a constraint to a variable based on the specified operation and value, only if the enforcer variable is true."""
    match operation:
        case ">":
            model.add(variable > value).OnlyEnforceIf(enforcer)
        case "<":
            model.add(variable < value).OnlyEnforceIf(enforcer)
        case ">=":
            model.add(variable >= value).OnlyEnforceIf(enforcer)
        case "<=":
            model.add(variable <= value).OnlyEnforceIf(enforcer)
        case "==":
            model.add(variable == value).OnlyEnforceIf(enforcer)
        case "!=":
            model.add(variable != value).OnlyEnforceIf(enforcer)

def find_relevant(taken_classes, All_Classes):
    #Helper function to optimize the solver by only including classes that are relevant to the taken_classes based on their prerequisites
    """Finds all classes that are relevant to the taken_classes based on their prerequisites. This includes the taken_classes themselves, their prerequisites, the prerequisites of their prerequisites, and so on."""
    ok_list = []
    def investigate(code):
        token_pattern = re.compile(r"""
        (\[.*?\])""", re.IGNORECASE | re.VERBOSE)

        if not isinstance(All_Classes[code].resid_prereq,float):
            matches = token_pattern.findall(All_Classes[code].resid_prereq)
        else:
            if code in ok_list:
                return
            else:
                ok_list.append(code)
        
        if code in ok_list:
            return
        else:
            ok_list.append(code)
            for match in matches:
                investigate(match.replace('[','').replace(']',''))
    for class_ in taken_classes:
        investigate(class_)
    return ok_list


class DCPSolver:
    #Class that initializes the solver and contains all of the functions for adding constraints and solving the problem
    def __init__(self,completed_credits: list,dcp_list: list,additional_completions: list):
        self.model = cp_model.CpModel()
        self.completed_credits = completed_credits
        self.dcp_list = dcp_list
        self.semester_domain = cp_model.Domain.FromIntervals([[1,8]])
        self.additional_completions = additional_completions

    def InitializeClasses(self, Unique_Courses_df: pd.DataFrame):
        """Initializes the All_Classes dictionary with Class objects for"""
        self.All_Classes = {}
        for _, c in Unique_Courses_df.iterrows():
            self.All_Classes[c['Code']] = Class(code = c['Code'], title = c['Title'],credits=c['Credits'],residential_prereqs=c['ResidentPrerequisites'],online_prereqs=c['OnlinePrerequisites'],offerings=c['Offered'],additional=c['RegistrationRestrictions'], model = self.model, semester_domain = self.semester_domain)
      
    def AddMeetingTimes(self,meeting_times_df: pd.DataFrame):
        """Adds meeting times to the options for each class based on the meeting_times_df dataframe."""
        for code in find_relevant(self.dcp_list, self.All_Classes):
            class_ = self.All_Classes[code]
            course_meeting_time_df = meeting_times_df[meeting_times_df['Course Code'].str.rstrip() == class_.code]
            class_.add_meeting_times(class_offerings_df = course_meeting_time_df)   

    def AddPrereqs(self):
        """Adds prerequisite constraints for each class based on the prerequisites specified in the Unique_Courses_df dataframe."""
        self.other_prereqs = []
        self.Semesters_Taken = {c.code: [c.semester_taken,c.is_present,c.prereq_enforced, c.transferred] for c in self.All_Classes.values()}
        for code in find_relevant(self.dcp_list, self.All_Classes):
            self.All_Classes[code].add_prerequisites(self.Semesters_Taken,self.completed_credits,self.All_Classes, self.additional_completions)
            for string in self.All_Classes[code].str_prereqs.keys():
                if string not in self.other_prereqs:
                    self.other_prereqs.append(string)
        
    def AddNoOverlaps(self):
        """Enforces no-overlap constraints for all of the residential class options based on their meeting times."""
        self.Days_Intervals = []
        for class_ in self.All_Classes.values():
            for option in class_.options:
                for day_interval in option.days_intervals:
                    self.Days_Intervals.append(day_interval)
        Days = set([day_interval.day for day_interval in self.Days_Intervals])
        for day in Days:
            day_intervals_list = [day_interval.interval for day_interval in self.Days_Intervals if day_interval.day == day]
            semester_list = [day_interval.semester_taken_interval for day_interval in self.Days_Intervals if day_interval.day == day]
            print(f'Setting No Overlap for {day}, here is len: {len(day_intervals_list)}')
            self.model.add_no_overlap_2d(day_intervals_list,semester_list)
    
    def AddCreditCap(self,max_credits = 18):
        """Enforces a credit cap for each semester based on the max_credits parameter, which is set to 18 by default."""
        for semester in range(1,9):
            credit_sum = []
            for code in find_relevant(self.dcp_list,self.All_Classes):
                class_ = self.All_Classes[code]
                is_taken_in_semester_i = self.model.new_bool_var(f'{class_.code}_taken_in_{semester}')
                self.model.add(class_.semester_taken == semester).OnlyEnforceIf(is_taken_in_semester_i)
                self.model.add(class_.semester_taken != semester).OnlyEnforceIf(is_taken_in_semester_i.Not())

                class_.credits_apply = self.model.new_bool_var(f'{class_.code}_credits_apply')        
                self.model.add_bool_and([is_taken_in_semester_i,class_.is_present]).OnlyEnforceIf(class_.credits_apply)
                self.model.add_bool_or([is_taken_in_semester_i.Not(),class_.is_present.Not()]).OnlyEnforceIf(class_.credits_apply.Not())

                credit_sum.append(class_.credits_apply*class_.credits)
            self.model.add(sum(credit_sum) <= max_credits)
    def Add_Required_Completed_Classes(self):
        """Enforces that all classes in the dcp_list are completed, and that all classes not in the dcp_list or completed_credits are not completed."""
        for c in self.All_Classes.values():
            if c.code in self.dcp_list:
                print(f'adding {c.code}')
                self.model.add(c.completed == True)
            if c.code not in find_relevant(self.dcp_list, self.All_Classes) and c.code not in self.completed_credits:
                self.model.add(c.completed == False)

            if c.code in self.completed_credits:
                print(f'completed {c.code}')
                self.model.add(c.transferred == True)
            else:
                self.model.add(c.transferred == False)

    def AddCustomConstraints(self, custom_constraints_df: pd.DataFrame):
        """Adds custom constraints based on the custom_constraints_df dataframe"""
        for _, constraint in custom_constraints_df.iterrows():
            for code in constraint['Affecting']:
                class_ = self.All_Classes[code]
                match constraint['Type']:
                    case 'Semester Taken':
                        apply_constraint(self.model,class_.semester_taken,constraint['Operation'],constraint['Value'],class_.is_present)
                    case 'Start Time':
                        for option in class_.options:
                            for day in option.days_intervals:
                                apply_constraint(self.model,day.start,constraint['Operation'],constraint['Value'],day.taken)

    def Solve(self):
        """Solves the model and prints the solution in a readable format."""
        self.solver = cp_model.CpSolver()
        status = self.solver.Solve(self.model)
        print(f"Solver status: {self.solver.StatusName(status)}")
        if status == cp_model.INFEASIBLE:
            print("The problem is infeasible - constraints are contradictory")
        elif status == cp_model.UNKNOWN:
            print("The solver couldn't determine feasibility within time limits")
        elif status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            print(f"No solution found! Status: {self.solver.StatusName(status)}")
        elif status == cp_model.OPTIMAL:
            solved_list = []

            present_classes = [c for c in self.All_Classes.values() if self.solver.Value(c.is_present) == True]

            for class_ in present_classes:
                for option in class_.options:
                    if not self.solver.Value(option.taken):
                        continue
                    else:
                        if option.offering == 'Online':
                            solved_list.append({
                                'Code': class_.code,
                                'Title': class_.title,
                                'Semester': int_to_semester(self.solver.Value(class_.semester_taken)),
                                'Credits': class_.credits,
                                'Type': 'Online',
                            })
                        else:
                            for day in option.days_intervals:
                                solved_list.append({
                                    'Code': class_.code,
                                    'Title': class_.title,
                                    'Semester': int_to_semester(self.solver.Value(class_.semester_taken)),
                                    'Credits': class_.credits,
                                    'Type': 'Residential',
                                    'Day': day.day,
                                    'Start_Time': int_to_time(day.start),
                                    'End_Time': int_to_time(day.end)
                                })
            
            self.solved_df = pd.DataFrame(solved_list).sort_values(by=['Code','Semester'])

    def DisplaySolution(self):
        """Prints the solution in a readable format, showing the classes taken each semester along with their meeting times if they are residential."""
        present_classes = [c for c in self.All_Classes.values() if self.solver.Value(c.is_present) == True]

        day_dict = {
            'Monday': 1,
            'Tuesday': 2,
            'Wednesday': 3,
            'Thursday': 4,
            'Friday': 5,
            'Saturday': 6,
            'Sunday': 7
        }

        for class_ in sorted(present_classes, key = lambda x: self.solver.Value(x.semester_taken)):
            for option in class_.options:
                if not self.solver.Value(option.taken):
                        continue
                print('\n',class_.code,f'({class_.credits} credits)','taken during',int_to_semester(self.solver.Value(class_.semester_taken))+':')
                if option.offering == 'Online':
                    print('Online\n')
                for day_interval in sorted(option.days_intervals, key = lambda x: day_dict[x.day]):
                    day = day_interval.day
                    start_time = int_to_time(self.solver.Value(day_interval.start))
                    end_time = int_to_time(self.solver.Value(day_interval.end))
                    print(day+':',start_time,'-',end_time)
        print(self.solved_df.head(20))

if __name__ == '__main__':
    #Example of how to use the DCPSolver class with some sample data. In practice, the completed_credits, dcp_list, additional_completions, max_credits, and custom_constraints_df variables would be populated based on user input or other sources of data.

    
    completed_credits = ['MATH 128'] #classes that have already been completed
    dcp_list = ['MATH 431'] #classes that need to be completed
    additional_completions = [] #additional completions related to the prerequisites for each class
    max_credits = 18 #maximum amount of credits to be taken each semester
    
    custom_constraints_df = pd.DataFrame([
    {
        'Affecting': ['MATH 132'],
        'Type': 'Start Time',
        'Operation': '>=',
        'Value': time_to_int('8:15 AM')
    },
    {
        'Affecting': ['MATH 131'],
        'Type': 'Semester Taken',
        'Operation': '>',
        'Value': 3 
    }]) #df of custom constraints that can be inputted by the user
    #can have operations <,>,<=,>=,==,!= with types "Semester Taken" and "Start Time". Semester Taken has freshman fall as "1", freshman spring as "2", etc

    #various backend dfs that should be static for each user
    Unique_Courses_df = pd.read_csv('..\\Data\\Course_Data.csv') #related to the prerequisites and information of the particular courses
    meeting_times_df = pd.read_csv('..\\Data\\Offerings.csv') #df of all of the offerings from a number of different semesters

    solver = DCPSolver(completed_credits,dcp_list,additional_completions)
    solver.InitializeClasses(Unique_Courses_df)
    solver.Add_Required_Completed_Classes()
    solver.AddMeetingTimes(meeting_times_df)
    solver.AddCreditCap(max_credits)
    solver.AddPrereqs()
    solver.AddNoOverlaps()
    solver.AddCustomConstraints(custom_constraints_df)
    solver.Solve()
    print(', '.join(solver.other_prereqs))
    solver.DisplaySolution()
    #print(solver.other_prereqs) for later when asking about what to put in for elements of "additional_completions"
    
def SolveForClassDF(completed_credits,dcp_list,additional_completions,Unique_Courses_df,meeting_times_df,max_credits,custom_constraints_df):
    solver = DCPSolver(completed_credits,dcp_list,additional_completions)
    solver.InitializeClasses(Unique_Courses_df)
    solver.Add_Required_Completed_Classes()
    solver.AddMeetingTimes(meeting_times_df)
    solver.AddCreditCap(max_credits)
    solver.AddPrereqs()
    solver.AddNoOverlaps()
    solver.AddCustomConstraints(custom_constraints_df)
    solver.Solve()
    return solver.solved_df