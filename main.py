import json

class Schedule:
    DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

    def __init__(self, schedule_data: list):
        # Initialize a nested dict: { "Saturday": {1: None, 2: None, ...}, ... }
        self.days = {day: {p: None for p in range(1, 7)} for day in self.DAYS}

        for session in schedule_data:
            day = session["day"]
            period = session["period"]

            if day in self.days and period in self.days[day]:
                self.days[day][period] = {
                    "name": session["course_name"],
                    "code": session["course_code"],
                    "type": session["type"],
                    "instructor": session["instructor"]
                }

    def print_schedule(self):
        for day, periods in self.days.items():
            print(f"\n{day}:")
            for period, session in periods.items():
                if session:
                    print(f"  Period {period}: {session['name']}, {session['type']}")
                else:
                    print(f"  Period {period}: Free")

    def gaps (self):
        gaps_count = 0
        for day in self.days:
            temp = 0
            for i in range(1, 6):
                if self.days[day][i] is not None:
                    for i in range(i+1, 6):
                        if self.days[day][i] is None:
                            temp += 1
                        else:
                            gaps_count += temp
                            break
        return gaps_count


# Usage
with open("CE01.json", encoding="utf-8") as file:
    sch_ce1 = json.load(file)

schedule = Schedule(sch_ce1)
schedule.print_schedule()
print(schedule.gaps())
