import { Container } from "react-bootstrap";
import { Route, Routes } from "react-router-dom";
import AuthRoute from "./components/AuthRoute";
import NavBar from "./components/NavBar";
// import Home from "./pages/Home";
import Login from "./pages/Login";
import MainChat from "./pages/MainChat";
import PasswordReset from "./pages/PasswordReset";
import Register from "./pages/Register";
import UpdatePassword from "./pages/UpdatePassword";


const App = () => {
  return (
    <>
      <NavBar />
      <Container style={{"paddingLeft": "0", "paddingRight": "0", "marginLeft": "0", "marginRight": "0"}}>
          <Routes>
            <Route element={<AuthRoute />}>
              <Route path="/" element={<MainChat />} />
              <Route path="/main-chat" element={<MainChat />} />
              {/* <Route path="/home" element={<Home />} /> */}
            </Route>
            <Route path="/register" element={<Register />} />
            <Route path="/login" element={<Login />} />
            <Route path="/passwordreset" element={<PasswordReset />} />
            <Route path="/update-password" element={<UpdatePassword />} />
            
          </Routes>
      </Container>
    </>
  );
};

export default App;
