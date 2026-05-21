from ortools.sat.python import cp_model 
import pandas as pd
import re

class Day_Interval:
    def __init__(self, code, day, start, end, semester, offering, taken, semester_taken_interval, num, model):
        self.code = code
        self.semester = semester
        self.offering = offering
        self.day = day
        self.start = time_to_int(start)
        self.end = time_to_int(end)
        self.duration = self.end - self.start
        self.taken = taken
        self.semester_taken_interval = semester_taken_interval
        self.interval = model.NewOptionalFixedSizeIntervalVar(self.start, self.duration, taken, f'{code}_{semester}_{day}_{start}_{num}')
    def summary(self):
        print(f'--Summary of {self.code} day interval--\nSemester: {self.semester}\nOffering: {self.offering}\nDay: {self.day}\nStart-End: {self.start} - {self.end}\n\n')  

class Option:
        def __init__(self, code, semester, semester_taken_interval, offering, day_and_times: dict, num:int, is_residential, model):
            self.semester = semester
            self.offering = offering
            self.num = num
            self.taken = model.NewBoolVar(f'{code}_{semester}_{num}')
            self.days_intervals = []
            self.day_times_dict = day_and_times
            self.code = code
            if day_and_times and offering in ['Residential','Both']:
                model.Add(self.taken == False).OnlyEnforceIf(is_residential.Not())
                for day, intervals in day_and_times.items():  
                    for interval_str in intervals.split(' | '):
                        start_time, end_time = interval_str.split(' - ')
                        NewInterval = Day_Interval(code,day,start_time,end_time,semester,offering,self.taken, semester_taken_interval, num, model)
                        self.days_intervals.append(NewInterval)
            else:
                model.Add(is_residential == False).OnlyEnforceIf(self.taken)
            
        def summary(self):
            print(f'Semester: {self.semester}\nDay and Times: {self.day_times_dict}\nCode: {self.code}\n\n')

class Node:
    def __init__(self, value: str, left, right, code, semester_map: dict,self_semester_taken,completed_credits,All_Classes,additional_completions,model):
        self.value = value
        self.left = left
        self.right = right
        self.code = code
        
        if value == 'or':
            self.var = model.NewBoolVar(f'or_{left.value}_{right.value}_for_{code}')
            model.AddBoolOr([left.var,right.var]).OnlyEnforceIf(self.var)
            model.AddBoolAnd([left.var.Not(),right.var.Not()]).OnlyEnforceIf(self.var.Not())
        elif value == 'and':
            self.var = model.NewBoolVar(f'and_{left.value}_{right.value}_for_{code}')
            model.AddBoolAnd([left.var,right.var]).OnlyEnforceIf(self.var)
            model.AddBoolOr([left.var.Not(),right.var.Not()]).OnlyEnforceIf(self.var.Not())
        else:
            self.var = model.NewBoolVar(f'{value}_for_{code}')
            prereq_code = value.split(']{')[0].replace('[','').replace(']','')
            if prereq_code in completed_credits:
                model.Add(self.var == True)
            elif prereq_code in semester_map.keys():
                prereq_semester_taken = semester_map[prereq_code][0]
                prereq_is_present = semester_map[prereq_code][1]
                prereq_prereq_enforced = semester_map[prereq_code][2]
                
                if 'concurrent' in value:
                    concurrent_semester_check = model.NewBoolVar(f'Concurrent_Or_Less_Semester_{prereq_code}_{self.code}')

                    model.Add(prereq_semester_taken <= self_semester_taken).OnlyEnforceIf(concurrent_semester_check)
                    model.Add(prereq_semester_taken > self_semester_taken).OnlyEnforceIf(concurrent_semester_check.Not())
                    
                    model.AddBoolAnd([prereq_is_present,concurrent_semester_check,prereq_prereq_enforced]).OnlyEnforceIf(self.var)
                    model.AddBoolOr([prereq_is_present.Not(),concurrent_semester_check.Not(),prereq_prereq_enforced.Not()]).OnlyEnforceIf(self.var.Not())

                else:
                    nonconcurrent_semester_check = model.NewBoolVar(f'NonConcurrent_Or_Less_Semester_{prereq_code}_{self.code}')

                    model.Add(prereq_semester_taken < self_semester_taken).OnlyEnforceIf(nonconcurrent_semester_check)
                    model.Add(prereq_semester_taken >= self_semester_taken).OnlyEnforceIf(nonconcurrent_semester_check.Not())

                    model.AddBoolAnd([prereq_is_present,nonconcurrent_semester_check]).OnlyEnforceIf(self.var)
                    model.AddBoolOr([prereq_is_present.Not(),nonconcurrent_semester_check.Not()]).OnlyEnforceIf(self.var.Not())
            else:
                All_Classes[self.code].str_prereqs[self.value] = self.var
                if self.value in additional_completions:
                    model.Add(self.var == True)
                else:
                    model.Add(self.var == False)
            

class Class:
    def __init__(self, code, title, credits, residential_prereqs, online_prereqs, offerings, additional, model, semester_domain):
        self.model = model
        if '-' in credits:
            self.credits = int(credits.split('-')[1])
        elif ',' in credits:
            self.credits = int(credits.split(',')[1])
        else:
            self.credits = int(credits)
        self.code = code
        self.title = title
        self.resid_prereq = residential_prereqs
        self.online_prereq = online_prereqs
        if isinstance(online_prereqs,float):
            self.online_prereq = residential_prereqs
        else:
            self.online_prereq = online_prereqs

        self.str_prereqs = {}
        
        self.additional = additional
        self.prereq_enforced = self.model.NewBoolVar(f'{self.code}_prereq_enforced')
        self.is_present = self.model.NewBoolVar(f'{self.code}_is_present')
        self.is_residential = self.model.NewBoolVar(f'{self.code}_offering')
        self.semester_taken = self.model.NewIntVarFromDomain(semester_domain, f'{self.code}_semester')
        self.semester_taken_interval = self.model.NewFixedSizeIntervalVar(self.semester_taken*100,1,f'{self.code}_semester_taken')

        self.is_fall = self.model.NewBoolVar(f'{code}_is_fall')
        q = self.model.NewIntVar(0, 5, f'q_{self.code}')  
        r = self.model.NewIntVar(0, 1, f'r_{self.code}')
        self.model.Add(self.semester_taken == 2 * q + r)
        
        self.model.Add(r == 1).OnlyEnforceIf(self.is_fall)
        self.model.Add(r == 0).OnlyEnforceIf(self.is_fall.Not())

        if offerings == 'Residential':
            self.offering = 'Residential'
            self.model.Add(self.is_residential == True)
        elif offerings == 'Online':
            self.offering = 'Online'
            self.model.Add(self.is_residential == False)
        else:
            self.offering = 'Both'

        self.transferred = self.model.NewBoolVar(f'{self.code}_transferred')
        
        self.model.Add(self.is_present == False).OnlyEnforceIf(self.transferred)

        self.completed = self.model.NewBoolVar(f'{self.code}_completed')

        self.model.AddBoolOr([self.transferred,self.is_present]).OnlyEnforceIf(self.completed)
        self.model.AddBoolAnd([self.transferred.Not(),self.is_present.Not()]).OnlyEnforceIf(self.completed.Not())
        self.options = []

    def add_meeting_times(self, class_offerings_df: pd.DataFrame):
        seen_intervals = []
        for index, class_offering in class_offerings_df.iterrows(): 
            semester = class_offering['Semester'].split()[0]
            
                
            if class_offering['Location'] != 'Online' and len(class_offering['Time'].split(' | ')) != 1:
                unique_str = class_offering['Time']+semester
                if unique_str in seen_intervals:
                    continue
                times_dict = {}
                for times in class_offering['Time'].split(' and '):
                    time_interval = times.split(' | ')[1]
                    for day in times.split(' | ')[0].split():
                        if times_dict.get('day'):
                            
                            times_dict[day] = times_dict[day] + f' | {time_interval}'
                        else:
                            times_dict[day] = time_interval
                option = Option(code = self.code,semester = semester, semester_taken_interval=self.semester_taken_interval, offering = 'Residential', day_and_times = times_dict, num = index, is_residential = self.is_residential,model= self.model)
                self.options.append(option)
                seen_intervals.append(unique_str)
            else:
                unique_str = 'Online '+semester
                if unique_str in seen_intervals:
                    continue
                option = Option(code = self.code, semester = semester, semester_taken_interval=self.semester_taken_interval, offering = 'Online', day_and_times={}, num = index, is_residential = self.is_residential,model = self.model)
                self.options.append(option)
                seen_intervals.append(unique_str)   
           
            
        #some option has to be taken if a class is taken
        if len([option.taken for option in self.options]) != 0:
            self.model.Add(sum([option.taken for option in self.options]) == 1).OnlyEnforceIf(self.is_present)
            self.model.Add(sum([option.taken for option in self.options]) == 0).OnlyEnforceIf(self.is_present.Not())
            #if taken in the fall or spring, fall semesters are odd
            fall_options = [option.taken for option in self.options if option.semester == 'Fall']
            spring_options = [option.taken for option in self.options if option.semester == 'Spring']
            self.model.Add(sum(fall_options) == 0).OnlyEnforceIf([self.is_fall.Not(), self.is_present])
            self.model.Add(sum(spring_options) == 0).OnlyEnforceIf([self.is_fall,self.is_present])
        else:
            self.model.Add(self.is_present == False)
    
    def add_prerequisites(self, semester_map: dict,completed_credits,All_Classes,additional_completions):
        def parse_acceptably(string: str):
            
            token_pattern = re.compile(r"""
                (\()                                      # Group 1: Opening parenthesis
            |   (\))                                      # Group 2: Closing parenthesis
            |   (\[[^\[\]]+\]\{[^{}]+\})                  # Group 3: [Course]{modifier}
            |   (\[[^\[\]]+\])                            # Group 4: [Course]
            |   (\band\b|\bor\b|\bnot\b)                  # Group 5: Logical operators
            |   ([^()\[\]\s]+(?:\s(?!and\b|or\b|not\b)[^()\[\]\s]+)*)   # Group 6: Other phrases
            """, re.IGNORECASE | re.VERBOSE)

            matches = token_pattern.findall(string)

            # Flatten and strip non-empty matches
            tokens = [token.strip() for group in matches for token in group if token]

            output = []
            stack = []
            precedence = {
                'and': (2, 'left'),
                'or':  (1, 'left'),
            }
            for token in tokens:
                if token == '(':
                    stack.append(token)
                elif token == ')':
                    while stack and stack[-1] != '(':
                        output.append(stack.pop())
                    stack.pop()
                elif token in ['and', 'or']:
                    while (stack and stack[-1] in ['and', 'or']) and (precedence[token][0] <= precedence[stack[-1]][0]):
                        output.append(stack.pop())
                    stack.append(token)
                else:
                    output.append(token)
            while stack:
                output.append(stack.pop())
            cleaned_tokens = output
            return cleaned_tokens

        def build_ast(tokens):
            stack = []
            for token in tokens:
                if token in ['and', 'or']:
                    right = stack.pop()
                    left = stack.pop()
                    node = Node(token, left, right, self.code, semester_map, self.semester_taken, completed_credits, All_Classes, additional_completions,self.model)
                    stack.append(node)
                else:
                    stack.append(Node(token, None, None, self.code, semester_map, self.semester_taken, completed_credits, All_Classes, additional_completions,self.model))
            return stack[0]
        
        if not isinstance(self.resid_prereq, float):    
            resid_tokens = parse_acceptably(self.resid_prereq)
            self.resid_prereq_tree = build_ast(resid_tokens)
            self.resid_prereq_enforced = self.resid_prereq_tree.var
            
            self.model.Add(self.resid_prereq_enforced == True).OnlyEnforceIf([self.is_present,self.is_residential])
        else:
            self.resid_prereq_enforced = self.model.NewBoolVar(f'{self.code}_resid_prereq_enforced')


        if not isinstance(self.online_prereq,float):
            online_tokens = parse_acceptably(self.online_prereq)
            self.online_prereq_tree = build_ast(online_tokens)
            self.online_prereq_enforced = self.online_prereq_tree.var

            self.model.Add(self.online_prereq_enforced == True).OnlyEnforceIf([self.is_present,self.is_residential.Not()]) 
        else:
            self.online_prereq_enforced = self.model.NewBoolVar(f'{self.code}_online_prereq_enforced')
        
        self.model.AddBoolOr([self.resid_prereq_enforced,self.online_prereq_enforced]).OnlyEnforceIf(self.prereq_enforced)
        self.model.AddBoolAnd([self.resid_prereq_enforced.Not(),self.online_prereq_enforced.Not()]).OnlyEnforceIf(self.prereq_enforced.Not())
    def __getitem__(self,key):
        match key:
            case 'code':
                return self.code
            case 'title':
                return self.title
            case 'completed':
                return self.completed
            case 'credits':
                return self.credits
            case 'is_fall':
                return self.is_fall
            case 'semester_taken':
                return self.semester_taken

def time_to_int(time: str):
    hours, stuff = time.split(':')
    minutes, type = stuff.split()
    time_min = int(minutes)
    
    if type.lower() == 'pm' and int(hours) != 12:
        time_min += (int(hours) + 12) * 60
    elif type.lower() == 'am' and int(hours) == 12:
        time_min += 0  # 12 AM is midnight
    else:
        time_min += int(hours) * 60
    
    return time_min

def int_to_semester(num:int):
    dict = {1:'Freshman Fall',
            2:'Freshman Spring',
            3:'Sophomore Fall',
            4:'Sophomore Spring',
            5:'Junior Fall',
            6:'Junior Spring',
            7:'Senior Fall',
            8:'Senior Spring'
            }
    return dict[num]

def int_to_time(num:int):
    q, r = divmod(num, 60)
    if q == 24:
        return f'{q:02}:{r:02} AM'
    elif q > 12:
        q-=12
        return f'{q:02}:{r:02} PM'
    elif q == 0:
        return f'{q+12:02}:{r:02} AM'
    else:
        return f'{q:02}:{r:02} AM'

def apply_constraint(model:cp_model.CpModel, variable, operation:str, value:int, enforcer):
    match operation:
        case ">":
            model.Add(variable > value).OnlyEnforceIf(enforcer)
        case "<":
            model.Add(variable < value).OnlyEnforceIf(enforcer)
        case ">=":
            model.Add(variable >= value).OnlyEnforceIf(enforcer)
        case "<=":
            model.Add(variable <= value).OnlyEnforceIf(enforcer)
        case "==":
            model.Add(variable == value).OnlyEnforceIf(enforcer)
        case "!=":
            model.Add(variable != value).OnlyEnforceIf(enforcer)

def find_relevant(taken_classes, All_Classes):
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
    def __init__(self,completed_credits: list,dcp_list: list,additional_completions: list):
        self.model = cp_model.CpModel()
        self.completed_credits = completed_credits
        self.dcp_list = dcp_list
        self.semester_domain = cp_model.Domain.FromIntervals([[1,8]])
        self.additional_completions = additional_completions

    def InitializeClasses(self, Unique_Courses_df: pd.DataFrame):
        self.All_Classes = {}
        for _, c in Unique_Courses_df.iterrows():
            self.All_Classes[c['Code']] = Class(code = c['Code'], title = c['Title'],credits=c['Credits'],residential_prereqs=c['ResidentPrerequisites'],online_prereqs=c['OnlinePrerequisites'],offerings=c['Offered'],additional=c['RegistrationRestrictions'], model = self.model, semester_domain = self.semester_domain)
      
    def AddMeetingTimes(self,meeting_times_df: pd.DataFrame):
        for code in find_relevant(self.dcp_list, self.All_Classes):
            class_ = self.All_Classes[code]
            course_meeting_time_df = meeting_times_df[meeting_times_df['Course Code'].str.rstrip() == class_.code]
            class_.add_meeting_times(class_offerings_df = course_meeting_time_df)   

    def AddPrereqs(self):
        self.other_prereqs = []
        self.Semesters_Taken = {c.code: [c.semester_taken,c.is_present,c.prereq_enforced, c.transferred] for c in self.All_Classes.values()}
        for code in find_relevant(self.dcp_list, self.All_Classes):
            self.All_Classes[code].add_prerequisites(self.Semesters_Taken,self.completed_credits,self.All_Classes, self.additional_completions)
            for string in self.All_Classes[code].str_prereqs.keys():
                if string not in self.other_prereqs:
                    self.other_prereqs.append(string)
        
    def AddNoOverlaps(self):
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
            self.model.AddNoOverlap2D(day_intervals_list,semester_list)
    
    def AddCreditCap(self,max_credits = 18):
        for semester in range(1,9):
            credit_sum = []
            for code in find_relevant(self.dcp_list,self.All_Classes):
                class_ = self.All_Classes[code]
                is_taken_in_semester_i = self.model.NewBoolVar(f'{class_.code}_taken_in_{semester}')
                self.model.Add(class_.semester_taken == semester).OnlyEnforceIf(is_taken_in_semester_i)
                self.model.Add(class_.semester_taken != semester).OnlyEnforceIf(is_taken_in_semester_i.Not())

                class_.credits_apply = self.model.NewBoolVar(f'{class_.code}_credits_apply')        
                self.model.AddBoolAnd([is_taken_in_semester_i,class_.is_present]).OnlyEnforceIf(class_.credits_apply)
                self.model.AddBoolOr([is_taken_in_semester_i.Not(),class_.is_present.Not()]).OnlyEnforceIf(class_.credits_apply.Not())

                credit_sum.append(class_.credits_apply*class_.credits)
            self.model.Add(sum(credit_sum) <= max_credits)
    def Add_Required_Completed_Classes(self):
        for c in self.All_Classes.values():
            if c.code in self.dcp_list:
                print(f'adding {c.code}')
                self.model.Add(c.completed == True)
            if c.code not in find_relevant(self.dcp_list, self.All_Classes) and c.code not in self.completed_credits:
                self.model.Add(c.completed == False)

            if c.code in self.completed_credits:
                print(f'completed {c.code}')
                self.model.Add(c.transferred == True)
            else:
                self.model.Add(c.transferred == False)

    def AddCustomConstraints(self, custom_constraints_df: pd.DataFrame):
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
            self.solved_df = []

            present_classes = [c for c in self.All_Classes.values() if self.solver.Value(c.is_present) == True]

            for class_ in present_classes:
                for option in class_.options:
                    if not self.solver.Value(option.taken):
                        continue
                    else:
                        if option.offering == 'Online':
                            self.solved_df.append({
                                'Code': class_.code,
                                'Title': class_.title,
                                'Semester': int_to_semester(self.solver.Value(class_.semester_taken)),
                                'Credits': class_.credits,
                                'Type': 'Online',
                            })
                        else:
                            for day in option.days_intervals:
                                self.solved_df.append({
                                    'Code': class_.code,
                                    'Title': class_.title,
                                    'Semester': int_to_semester(self.solver.Value(class_.semester_taken)),
                                    'Credits': class_.credits,
                                    'Type': 'Residential',
                                    'Day': day.day,
                                    'Start_Time': int_to_time(day.start),
                                    'End_Time': int_to_time(day.end)
                                })
            
            self.solved_df = pd.DataFrame(self.solved_df).sort_values(by=['Code','Semester'])

    def DisplaySolution(self):
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
    Unique_Courses_df = pd.read_csv('Course_Data.csv') #related to the prerequisites and information of the particular courses
    meeting_times_df = pd.read_csv('Offerings.csv') #df of all of the offerings from a number of different semesters

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