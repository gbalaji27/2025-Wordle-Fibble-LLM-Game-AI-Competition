from enum import Enum


class Feedback(Enum):
    correct = "correct"
    present = "present"
    incorrect = "incorrect"


class LetterCell:
    def __init__(self):
        self.letter: str = ""
        self.feedback: Feedback = Feedback.incorrect
    
    def set_letter(self, letter: str):
        self.letter = letter.upper()
    
    def set_feedback(self, feedback: Feedback):
        self.feedback = feedback
