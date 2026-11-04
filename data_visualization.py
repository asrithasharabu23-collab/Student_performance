import pandas as pd

# Load dataset
data = pd.read_csv("students.csv")

# Display original dataset
print("Original Dataset")
print(data)

# Check missing values
print("\nMissing Values")
print(data.isnull().sum())

# Remove duplicate records
data = data.drop_duplicates()

# Fill missing values if any
data = data.fillna(data.mean(numeric_only=True))

# Check duplicate records
print("\nDuplicate Records")
print(data.duplicated().sum())

# Display cleaned dataset
print("\nCleaned Dataset")
print(data)

# Save cleaned dataset
data.to_csv("cleaned_students.csv", index=False)

print("\nDataset cleaned successfully!")

import matplotlib.pyplot as plt

# Graph 1: Study Hours vs Final Marks

plt.scatter(
    data["study_hours"],
    data["final_score"]
)

plt.xlabel("Study Hours")
plt.ylabel("Final Marks")
plt.title("Study Hours vs Final Marks")

plt.show()


# Graph 2: Attendance vs Final Marks

plt.scatter(
    data["attendance"],
    data["final_score"]
)

plt.xlabel("Attendance")
plt.ylabel("Final Marks")
plt.title("Attendance vs Final Marks")

plt.show()


# Graph 3: Average Marks

average_marks = data[
    [
        "previous_score",
        "assignment_score",
        "final_score"
    ]
].mean()

average_marks.plot(kind="bar")

plt.title("Average Student Marks")
plt.ylabel("Marks")

plt.show()