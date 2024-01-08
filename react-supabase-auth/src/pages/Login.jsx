import { useRef, useState } from "react";
import { Alert, Button, Card, Form } from "react-bootstrap";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthProvider";

const Login = () => {
  const emailRef = useRef(null);
  const passwordRef = useRef(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  // const handleSubmit = async (e) => {
  //   e.preventDefault();
  //   try {
  //     setErrorMsg("");
  //     setLoading(true);
  //     if (!passwordRef.current?.value || !emailRef.current?.value) {
  //       setErrorMsg("Please fill in the fields");
  //       return;
  //     }
  //     const {
  //       data: { user, session },
  //       error
  //     } = await login(emailRef.current.value, passwordRef.current.value);
  //     if (error) setErrorMsg(error.message);
  //     if (user && session) navigate("/");
  //   } catch (error) {
  //     setErrorMsg("Email or Password Incorrect");
  //   }
  //   setLoading(false);
  // };
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setErrorMsg("");
      setLoading(true);
      if (!passwordRef.current?.value || !emailRef.current?.value) {
        setErrorMsg("Please fill in the fields");
        return;
      }

      // // Send a GET request to the 'api/test/' endpoint
      // const response = await fetch("http://127.0.0.1:8000/api/test/");
      // const data = await response.json();

      // // Log the response data to the console
      // console.log(data);

      // Assuming 'login' is a function that authenticates the user
      const {
        data: { user, session },
        error,
      } = await login(emailRef.current.value, passwordRef.current.value);

      if (error) setErrorMsg(error.message);
      if (user && session) navigate("/");
    } catch (error) {
      setErrorMsg("Failed to fetch API or Email or Password Incorrect");
      console.log(error);
    }
    setLoading(false);
  };


  return (
    <div className="auth-wrapper">
      <Card className="custom-card">
        <Card.Body>
          <h2 className="text-center mb-4">Login</h2>
          <Form onSubmit={handleSubmit}>
            <Form.Group id="email">
              <Form.Label>Email</Form.Label>
              <Form.Control type="email" ref={emailRef} required />
            </Form.Group>
            <Form.Group id="password">
              <Form.Label>Password</Form.Label>
              <Form.Control type="password" ref={passwordRef} required />
            </Form.Group>
            {errorMsg && (
              <Alert
                variant="danger"
                onClose={() => setErrorMsg("")}
                dismissible>
                {errorMsg}
              </Alert>
            )}
            <div className="text-center mt-2">
              <Button disabled={loading} type="submit" className="w-50 custom-register-button">
                Login
              </Button>
            </div>
          </Form>
        </Card.Body>
        <div className="w-100 text-center mt-2">
          New User? <Link to={"/register"}>Register</Link>
        </div>
        <div className="w-100 text-center mt-2">
          Forgot Password? <Link to={"/passwordreset"}>Click Here</Link>
        </div>
      </Card>
    </div>
  );
};

export default Login;