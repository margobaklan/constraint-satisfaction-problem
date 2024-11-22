from data import DAYS, TIMESLOTS
import csv
from data import SUBJECTS, AUDITORIUMS, TEACHERS, TIMESLOTS, DAYS


def getValidTeacher(subject_name, lesson_type):
    valid_subject_teachers = [teacher for teacher in TEACHERS if subject_name in teacher.subject_taught]
    valid_subject_teachers = [teacher for teacher in valid_subject_teachers if lesson_type in teacher.subject_type]
    return valid_subject_teachers


def generate_data():
    variables = []
    domains = {}
    constraints = {}

    for subject in SUBJECTS:
        for i in range(subject.lectures_number):
            variables.append((subject.subject_name, subject.group, 'Лекція', i))
        for i in range(subject.practice_number):
            variables.append((subject.subject_name, subject.group, 'Практика', i))

    timeslots = [(day, time) for day in DAYS for time in TIMESLOTS]

    for variable in variables:
        subject_name, group, lesson_type, iterator = variable
        suitable_teachers = getValidTeacher(subject_name, lesson_type)
        domains[variable] = [
            (time_slot, auditorium, teacher)
            for time_slot in timeslots
            for auditorium in AUDITORIUMS
            for teacher in suitable_teachers
        ]

        constraints[variable] = []

        for other_variable in variables:
            if variable == other_variable:
                continue
            other_subject_name, other_group, _, _ = other_variable

            if group == other_group:
                constraints[variable].append(other_variable)
            if subject_name == other_subject_name:
                constraints[variable].append(other_variable)

    return variables, domains, constraints

import os
def write_schedule_to_txt(assignment, output_dir="schedules"):
    os.makedirs(output_dir, exist_ok=True)

    schedule_by_group = {}
    for (subject, group, lesson_type, i), (time_slot, auditorium, teacher) in assignment.items():
        day, time = time_slot
        if group not in schedule_by_group:
            schedule_by_group[group] = {}
        if day not in schedule_by_group[group]:
            schedule_by_group[group][day] = []
        schedule_by_group[group][day].append((time, subject, lesson_type, auditorium, teacher.name))

    for group, days in schedule_by_group.items():
        file_path = os.path.join(output_dir, f"{group}_schedule.txt")
        with open(file_path, mode='w', encoding='utf-8') as file:
            file.write(f"Schedule for Group: {group}\n\n")
            for day in DAYS:
                if day in days:
                    file.write(f"{day}:\n")
                    for time, subject, lesson_type, auditorium, teacher in sorted(days[day], key=lambda x: TIMESLOTS.index(x[0])):
                        file.write(f"  {time}: {subject} ({lesson_type}) in {auditorium}, taught by {teacher}\n")
                    file.write("\n")

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables #subj, group, type_class
        self.domains = domains #timeslot, aud, teacher
        self.constraints = constraints 
        self.number_of_steps = 0

    def is_consistent(self, assignment, variable, value, group_timeslots, teacher_assignments):
        time_slot, auditorium, teacher = value
        day, time = time_slot
        subject_name, group, lesson_type, iterator = variable

        for other_var, assigned_value in assignment.items():
            other_subject, other_group, _, _ = other_var
            assigned_time_slot, assigned_auditorium, assigned_teacher = assigned_value
            if assigned_time_slot == time_slot and assigned_teacher == teacher: return False
            if assigned_time_slot == time_slot and assigned_auditorium == auditorium: return False
        if group.number_of_students > auditorium.capacity: return False
        if time_slot in group_timeslots[group][day] or len(group_timeslots[group][day]) >= len(TIMESLOTS):  # group timeslot taken
            return False

        group_timeslots[group][day].add(time_slot)

        if teacher in teacher_assignments:
            assigned_time_slot, _ = teacher_assignments[teacher]
            if assigned_time_slot == time_slot:  # teacher taken
                return False
        teacher_assignments[teacher] = (time_slot, subject_name)
        return True

    def select_unassigned_variable(self, assignment):
        unassigned_vars = [var for var in self.variables if var not in assignment.keys()]

        if len(unassigned_vars) == 0: return None
        def min_remaining(uv):
            minimal_remained_len = min(len(self.domains[var]) for var in uv)
            return [var for var in uv if len(self.domains[var]) == minimal_remained_len]

        mrv = min_remaining(unassigned_vars)
        if len(mrv) == 1:
            return mrv[0]

        def degree(uv):
            variable_degree = {}
            for var in uv:
                variable_degree[var] = 0
                lookup_vars = [c_var for c_var in uv if c_var != var]
                for lookup_var in lookup_vars:
                    for elem in self.constraints[lookup_var]:
                        if elem == var:
                            variable_degree[var] += 1
            sorted_by_degree = dict(sorted(variable_degree.items(), key=lambda item: item[1], reverse=True))
            return next(iter(sorted_by_degree))

        max_constraint_var = degree(mrv)
        return max_constraint_var

    def order_domain_values(self, assignment, variable):
        def count_constraints(value):
            constraints_removed = 0
            for var in self.constraints[variable]:
                if var not in assignment and value in self.domains[var]:
                    constraints_removed += 1
            return constraints_removed

        variable_values = self.domains[variable].copy()
        constraints_count = {v: count_constraints(v) for v in variable_values}
        return sorted(variable_values, key=lambda v: constraints_count[v])

    def backtrack(self, assignment, group_timeslots, teacher_assignments):
        if len(assignment) == len(self.variables):
            return assignment
        var = self.select_unassigned_variable(assignment)

        for value in self.order_domain_values(assignment, var):
            if self.is_consistent(assignment, var, value, group_timeslots, teacher_assignments):
                assignment[var] = value

                time_slot, auditorium, teacher = value
                day, time = time_slot
                subject_name, group, lesson_type, iterator = var

                result = self.backtrack(assignment, group_timeslots, teacher_assignments)
                if result is not None:
                    return result

                del assignment[var]
                group_timeslots[group][day].remove(time_slot)
                del teacher_assignments[teacher]

        return assignment

    def solve(self):
        groups = list(set([var[1] for var in self.variables]))
        assignment = {}
        group_timeslots = {group: {day: set() for day in DAYS} for group in groups}
        teacher_assignments = {}
        assignment = self.backtrack(assignment, group_timeslots, teacher_assignments)
        if len(assignment) == len(self.variables):
            print('Solution saved')
        return assignment


variables, domains, constraints = generate_data()
csp_solver = CSP(variables, domains, constraints)
schedule = csp_solver.solve()
write_schedule_to_txt(schedule)