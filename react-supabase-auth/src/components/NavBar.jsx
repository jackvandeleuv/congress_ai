import { Button } from "react-bootstrap";
import Container from "react-bootstrap/Container";
import Nav from "react-bootstrap/Nav";
import Navbar from "react-bootstrap/Navbar";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthProvider";

const NavBar = () => {
  const { auth, signOut } = useAuth();

  const handleLogout = async (e) => {
    e.preventDefault();
    try {
      const { error } = await signOut();
      console.log(error);
    } catch (error) {
      console.log(error);
    }
  };

  return (
    <Navbar collapseOnSelect className="custom-navbar" variant="dark">
      <Container>
        <Navbar.Brand>
        <img
          src="/img/congress_logo.png"
          width="30"
          height="30"
          className="d-inline-block align-top"
          alt="Logo"
        />
        CongressGPT</Navbar.Brand>
        <Navbar.Toggle aria-controls="responsive-navbar-nav" />
        <Navbar.Collapse id="responsive-navbar-nav">
          <Nav className="me-auto">
            {!auth && (
              <Nav.Link as={Link} to="/login" className="nav-link">
                Login
              </Nav.Link>
            )}
            {!auth && (
              <Nav.Link as={Link} to="/register" className="nav-link">
                Register
              </Nav.Link>
            )}
            {auth && (
              <Nav.Link as={Link} to="/" className={'nav-link'}>
                Home
              </Nav.Link>
            )}

            {/* {auth && (
              <Nav.Link as={Link} to="/history">
                History
              </Nav.Link>
            )}     */}
          </Nav>
          <Nav>
            {auth && (
              <Nav.Link as={Button} onClick={handleLogout} className={'nav-button'}>
                Log Out
              </Nav.Link>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default NavBar;