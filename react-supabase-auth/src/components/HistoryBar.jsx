import React, { useState, useEffect } from 'react';
import ListGroup from 'react-bootstrap/ListGroup';
import { useAuth } from "../context/AuthProvider";
import "./bar.css";
import PropTypes from 'prop-types';
import GridLoader from 'react-spinners/GridLoader';
import ContentLoader from 'react-content-loader';


const HistoryBar = ({ sessionToken, onLoading, onClick, highestChatId, handleNewChatButtonClick, nowChat }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  // const { sessionToken } = useAuth();
  // const API_HOST = 'http://localhost:8000';
  const API_HOST = '/api';

  // const truncateTitle = (title) => {
  //   return title.length > 50 ? title.substring(0, 50) + "..." : title;
  // }
  
  async function getCsrfToken() {
    const response = await fetch(`${API_HOST}/congressgpt/csrf`, {
      credentials: 'include',
    });

    if (response.ok) {
      const data = await response.json();
      return data.csrfToken;
    } else {
      console.error('API request failed');
    }
  }

  async function getHistoryBar() {
    try {
      if (!sessionToken) {
        console.error('Session token not available');
        return;
      }
      const response = await fetch(`${API_HOST}/congressgpt/get_historybar`, {
        credentials: 'include',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': await getCsrfToken(),
        },
        body: JSON.stringify({ token: sessionToken }),
      });

      if (response.ok) {
        const result = await response.json();
        const searchResult = result.chats;
        return searchResult;
      } else {
        console.error('API request failed');
      }
    } catch (error) {
      console.error('Error making API request:', error);
    }
  }

  useEffect(() => {
    const fetchData = async () => {
      onLoading(() => true);
      setLoading(true);
      const newData = await getHistoryBar();
      setData(newData || []);
      onLoading(() => false);
      setLoading(false);
    };

    fetchData();
  }, [sessionToken, highestChatId]); // Empty dependency array to run the effect only once
  
  return (
    <div className="scrollable-list">

      <div className='new-chat-div'>
        <button 
          className='new-chat-button'
          onClick={handleNewChatButtonClick}
        >
          New Chat
        </button>
      </div>

      <ListGroup defaultActiveKey="#link1">
        <ListGroup.Item>
          My Chat History
        </ListGroup.Item>
        {loading ? (
          <ListGroup.Item>Loading...</ListGroup.Item>
        ) : (
          data.map((item, index) => (
            <ListGroup.Item
              key={item.chatId}
              action
              active={item.chatId === nowChat}
              href={`#link${item.chatId}`}
              onClick={(event) => {
                event.preventDefault();
                onClick(item);
              }}
            >
              {item.title}
              {/* {truncateTitle(item.title)} */}
            </ListGroup.Item>
          ))
        )}
      </ListGroup>   
    </div>
  );
};

HistoryBar.propTypes = {
  sessionToken: PropTypes.string,
  onLoading: PropTypes.func,
  onClick: PropTypes.func,
  highestChatId: PropTypes.number,
  handleNewChatButtonClick: PropTypes.func,
  nowChat: PropTypes.number
};

export default HistoryBar;

