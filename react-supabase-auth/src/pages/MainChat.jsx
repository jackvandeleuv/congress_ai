import { useState, useEffect, useRef } from 'react';
import './ChatInterface.css'
import { useAuth } from "../context/AuthProvider";
import HistoryBar from "../components/HistoryBar";
import Message from "../components/Message";
import { jwtDecode } from 'jwt-decode';
import { supabase } from "../supabase/client";
import ModelSelector from '../components/ModelSelector';
import BeatLoader from 'react-spinners/BeatLoader';


const MainChat = () => {
  const API_HOST = '/api';
  const {user} = useAuth();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [nowChat, setNowChat] = useState();
  const [inputDisabled, setInputDisabled] = useState(false);
  const [messages, setMessages] = useState([]);
  const endOfMessagesRef = useRef(null);
  const [highestChatId, setHighestChatId] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  let _csrfToken = null;
  const [selectedModel, setSelectedModel] = useState('gpt-4-1106-preview');

  useEffect(() => {
    if (nowChat) {
      setHighestChatId(prevId => (prevId && prevId > nowChat) ? prevId : nowChat);
    }
  }, [nowChat]);

  const countWords = str => {
    return str.split(/\s+/).filter(Boolean).length;
  };


  const isTokenExpired = (token) => {
    if (!token) {
      // Token is considered expired if it's not present
      return true;
    }
    try {
      // Decode the JWT to get information about the token, such as expiration time
      const decodedToken = jwtDecode(token);

      // Get the current timestamp
      const currentTime = Date.now() / 1000; // Convert to seconds

      // Compare the expiration time with the current time
      // console.log(decodedToken.exp, currentTime)
      // console.log(decodedToken.exp < currentTime)
      return decodedToken.exp < currentTime;
    } catch (error) {
      console.error('Error decoding JWT:', error);
      return true;
    }
  };

  useEffect(() => {
    const fetchToken = async () => {
      try {
        // Check if the session token is expired
        if (!sessionToken || isTokenExpired(sessionToken)) {
          // Refresh the session token
          const { data, error } = await supabase.auth.refreshSession();

          if (error) {
            console.error('Error refreshing session:', error);
          } else {
            // Check if the new session token is available
            const { session } = data || {};
            const newToken = session?.access_token;

            if (newToken) {
              setSessionToken(newToken);
            } else {
              console.error('New session token not available after refresh');
            }
          }
        }
      } catch (error) {
        console.error('Error in fetchToken:', error);
      }
    };
    fetchToken();
  }, [sessionToken]);


  async function getCsrfToken() {
    if (_csrfToken === null) {

      const response = await fetch(`${API_HOST}/congressgpt/csrf`, {
        credentials: 'include',
      });

      if (response.ok) {
          const data = await response.json();
          _csrfToken = data.csrfToken;
          return _csrfToken;
      } else {
          console.error('API request failed');
      }
    }
  }

  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(scrollToBottom, [nowChat]);
  
  const handleInputChange = (e) => {
    setInput(e.target.value);
  };


  const handleSubmit = async (e) => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });

    e.preventDefault();
    const wordCount = countWords(input);
    if (wordCount > 500) {
      alert("Please keep your input query shorter than 500 words.");
      return;
    }
    if (!input.trim()) return;

    // Add user query to the chat
    const userQuery = {
      author: 'user',
      content: input,
      orderInChat: messages.length > 0 ? messages[messages.length - 1].orderInChat + 1 : 0,
      rating: 0,
      chatId: nowChat,
      searchResponse: false,
      searchRequest: false,
      isOpen: false
    }

    setMessages([...messages, userQuery]);

    // Reset the input field
    setInput('');
    setInputDisabled(true);
    setLoading(true);

    try {
      const storedInput = input;

      const csrfToken = await getCsrfToken()

      const response = await fetch(`${API_HOST}/congressgpt/ask`, {
        credentials: 'include',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
          user_input: storedInput,
          email: user.email,
          password: sessionToken,
          order_in_chat: messages.length > 0 ? messages[messages.length - 1].orderInChat + 1 : 0,
          chat_id: nowChat,
          created_at: new Date().toISOString(),  // Current timestamp,
          language_model: selectedModel
        },
        ),
      });

      if (response.ok) {
        const searchResult = await response.json();

        const botResponse = {
          author: 'bot',
          content: searchResult.content,
          rating: 0,
          orderInChat: searchResult.orderInChat,
          chatId: Number(searchResult.chatId),
          searchResponse: searchResult.searchResponse,
          searchRequest: searchResult.searchRequest,
          isOpen: false
        }

        setMessages((prevMessages) => [...prevMessages, botResponse]);

        if (typeof nowChat === 'undefined' || nowChat === null) {
          setNowChat(Number(searchResult.chatId));
        }

        if (searchResult.searchRequest) {
          const mSearch = await fetch(`${API_HOST}/congressgpt/search`, {
            credentials: 'include',
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
              chat_id: searchResult.chatId,
              password: sessionToken,
              language_model: selectedModel
            },
            ),
          });

          const { response: mSearchRes } = await mSearch.json()
          const mMessage = mSearchRes.map(item => {
            return {
              author: 'bot',
              content: item.content,
              rating: 0,
              orderInChat: item.orderInChat,
              chatId: item.chatId,
              searchResponse: item.searchResponse,
              searchRequest: item.searchRequest,
              isOpen: false
            }
          })
          setMessages(prevMessages => [...prevMessages, ...mMessage]);
        }
      } else {
        console.error('API request failed');
      }
    } catch (error) {
      console.error('Error making API request:', error);
    } finally {
      setLoading(false);
      setInputDisabled(false);
    }
    }; 

  
  async function handleNewChatButtonClick() {
    setNowChat(null);
    if (isTokenExpired(sessionToken)) {
      // Refresh the session token
      const { data, error } = await supabase.auth.refreshSession();

      if (error) {
        console.error('Error refreshing session:', error);
      } else {
        // Check if the new session token is available
        const { session } = data || {};
        const newToken = session?.access_token;

        if (newToken) {
          setSessionToken(newToken);
        } else {
          console.error('New session token not available after refresh');
        }
      }
    }
    setMessages([]);
  }


  async function handleHistoryBarClick(item) {
    setNowChat(item.chatId);
    try {
      setLoading(true);

      if (isTokenExpired(sessionToken)) {
        // Refresh the session token
        const { data, error } = await supabase.auth.refreshSession();

        if (error) {
          console.error('Error refreshing session:', error);
        } else {
          // Check if the new session token is available
          const { session } = data || {};
          const newToken = session?.access_token;

          if (newToken) {
            setSessionToken(newToken);
          } else {
            console.error('New session token not available after refresh');
          }
        }
      }

      const response = await fetch(`${API_HOST}/congressgpt/get_history`, {
        credentials: 'include',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': await getCsrfToken(),
        },
        body: JSON.stringify({
          token: sessionToken,
          chat_id: `${item.chatId}`
        }),
      });

      if (response.ok) {
        const { history } = await response.json();
        const sortedHistory = history.sort((a, b) => a.orderInChat - b.orderInChat);

        setMessages(sortedHistory.map((item) => {
          return {
            author: item.role === 'assistant' ? 'bot' : item.role,
            content: item.content,
            rating: item.rating,
            orderInChat: item.orderInChat,
            chatId: item.chatId,
            searchResponse: item.searchResponse,
            searchRequest: item.searchRequest,
            isOpen: false
          };
        }));
      } else {
        console.error('API request failed');
      }

      setLoading(false);
    } catch (error) {
      console.error('Error making API request:', error);
    }
  }


    return (
      // <Spin
      //   tip='loading...'
      //   spinning={loading}
      // >
        <div className="chat-container">
            {/* <button className="current-chat-button" onClick={handleCurrentChatClick}>
                Current Chat
            </button> */}
          
            <HistoryBar 
              sessionToken={sessionToken}
              onLoading={(status) => setLoading(status)}
              highestChatId={highestChatId}
              onClick={handleHistoryBarClick}
              handleNewChatButtonClick={handleNewChatButtonClick}
              nowChat={nowChat}
            />

         {/* <button className="new-chat-button" onClick={startNewChat}>
                Start New Chat
            </button> */}

          <div className="chat-interface">

          <ModelSelector 
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
          />

            {/* <ul className="message-list">
              {messages.map((message, index) => (
                <li key={index} className={`message ${message.author}`}>
                  {message.content}
                </li>
              ))}
              <div ref={endOfMessagesRef} />
            </ul> */}

            <div className="message-list-wrapper">
              <ul className="message-list">
                {messages.map((message, index) => (
                  <li key={index} className={`message ${message.author} ${message.searchResponse ? 'search' : 'nonsearch'}`}>
                    <Message 
                        message={message} 
                        messages={messages}
                        setMessages={setMessages}
                        nowChat={nowChat}
                    />
                  </li>
                ))}
                <div ref={endOfMessagesRef} />
              </ul>
            </div>

            {/* {loading && 
              <div className="beat-loader">
                <BeatLoader
                  size={20}
                  color={"#3B3B3B"}
                  loading={true} 
                />
              </div>
            } */}

            <form className="input-form" onSubmit={handleSubmit}>
              {loading ? (
                <div className="input-loader">
                  <BeatLoader
                    size={20}
                    color={"black"}
                    loading={true}
                  />
                </div>
              ) : (
              <input
                type="text"
                value={input}
                onChange={handleInputChange}
                placeholder="Type your query here..."
                className="input-field"
                disabled={loading}
                
              />
              )}
              <button type="submit" className="submit-button">
                Send 
              </button>
            </form>
          </div>
        </div>
      // </Spin>
    );
}
export default MainChat;
