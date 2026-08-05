function Employee(props) {
  return (
    <div className="card">
      <h2>{props.name}</h2>

      <p>
        <strong>Employee ID:</strong> {props.id}
      </p>

      <p>
        <strong>Department:</strong> {props.department}
      </p>

      <p>
        <strong>Designation:</strong> {props.designation}
      </p>

      <p>
        <strong>Salary:</strong> {props.salary}
      </p>
    </div>
  );
}

export default Employee;
