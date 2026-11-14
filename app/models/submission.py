from dataclasses import dataclass


@dataclass
class Submission:
    id: str
    assignment_id: str
    user_id: str
    file_id: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_type: str
    file_size: int
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row):
        return cls(**dict(row))

    def public_dict(self):
        result = vars(self).copy()
        result.pop("file_path", None)
        return result
