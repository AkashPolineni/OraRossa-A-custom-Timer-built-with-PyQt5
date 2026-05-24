from storage import load_tasks, save_tasks

class TaskManager:

    def __init__(self):
        self.tasks = load_tasks()

    def add_task(self, title):

        if title.strip() == "":
            return

        self.tasks.append({
            "title": title,
            "completed": False
        })

        save_tasks(self.tasks)

    def complete_task(self, index):

        if 0 <= index < len(self.tasks):
            self.tasks[index]["completed"] = True
            save_tasks(self.tasks)

    def delete_task(self, index):

        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            save_tasks(self.tasks)

    def get_tasks(self):
        return self.tasks