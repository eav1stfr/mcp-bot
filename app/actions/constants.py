from enum import StrEnum


class ActionStatus(StrEnum):
    TODO = "todo"
    DONE = "done"


class ActionSetting(StrEnum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"


class ActionPrice(StrEnum):
    CHEAP = "cheap"
    MEDIUM = "medium"
    EXPENSIVE = "expensive"


class ActionErrorMessage(StrEnum):
    ACTION_NOT_FOUND = "Action not found"
