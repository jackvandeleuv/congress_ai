import PropTypes from 'prop-types';
import './Components.css';
import VoteButton from '../components/VoteButton';
import ExpandButtonSVG from '../assets/expand-button.svg';
import ExpandButtonActiveSVG from '../assets/expand-button-active.svg';


const Message = ({ message, messages, setMessages, nowChat }) => {

    function splitMessageContent(content) {
        if (typeof content === 'string' && content.startsWith('[{')) {
          const trimmedContent = content.slice(2, content.length - 2).replace(/<[^>]*>/g, '');
          // Split the string by '}, {'
          const splitContent = trimmedContent.split(/},\s*{/) 
          // const splitsplit = trimmedContent.split(', \'')
    
        // Remove any HTML tags
        return splitContent.map(element => 
          element.split(', \'').join('\n') + '\n\n'
        );
        // return splitContent.map(element => 
        //   element + '\n' + '\n'
        // );
        }
        return [content]; // Return content in an array if it's not a string starting with '[{'
    }

    function calculateMessageLabel(message) {
        if (message.author === 'user') return 'User';
        if (message.searchRequest === true) return 'Search Query';
        if (message.searchResponse === true) return 'Search Results';
        if (message.author === 'bot') return 'GPT';
        return '';
    }

    
    function toggleMessage(orderInChat) {
        const updatedMessages = [...messages];
        let i = 0;
        while (i < updatedMessages.length - 1 && updatedMessages[i].orderInChat !== orderInChat) i++;
        updatedMessages[i].isOpen = !updatedMessages[i].isOpen;
        setMessages(updatedMessages);
    }

    return (
        message.searchResponse ? (
            <div className={message.isOpen ? 'search-result-panel-open' : 'search-result-panel-closed'}>  
                {message.isOpen && <div className='expand-results'>
                    <img 
                        src={message.isOpen ? ExpandButtonActiveSVG : ExpandButtonSVG}
                        onClick={() => toggleMessage(message.orderInChat)}
                        className={"expand-button"}
                    />
                </div>}

                <div>
                    {message.isOpen ? (
                        <>
                            {splitMessageContent(message.content).map((part, partIndex) => (
                                <div key={partIndex} style={{ whiteSpace: 'pre-line' }}>
                                    {part}
                                </div>
                            ))}
                            <div className="message-info-panel">
                                {message.author === 'bot' ?  // The user only votes on bot messages
                                    <div className="vote-buttons">
                                    <VoteButton 
                                        isUpVoter={true}
                                        messages={messages}
                                        setMessages={setMessages}
                                        orderInChat={message.orderInChat}
                                        chatId={nowChat}
                                    />
                                    <VoteButton 
                                        isUpVoter={false}
                                        messages={messages}
                                        setMessages={setMessages}
                                        orderInChat={message.orderInChat}
                                        chatId={nowChat}
                                    />
                                    </div> 
                                    :
                                    <div></div>
                                }

                                <div className="message-label">
                                    {calculateMessageLabel(message)}
                                </div>
                             </div>
                        </>
                    ) : (
                        <>RESULTS RETURNED BY SEARCH ENGINE</>
                    )}
                </div>

                {!message.isOpen && <div className='expand-results'>
                    <img 
                        src={message.isOpen ? ExpandButtonActiveSVG : ExpandButtonSVG}
                        onClick={() => toggleMessage(message.orderInChat)}
                        className={"expand-button"}
                    />
                </div>}

            </div>
        ) : (
            <>
            {splitMessageContent(message.content).map((part, partIndex) => (
                <div key={partIndex} style={{ whiteSpace: 'pre-line' }}>
                    {part}
                </div>
            ))}
            
            <div className="message-info-panel">
              {message.author === 'bot' ?  // The user only votes on bot messages
                <div className="vote-buttons">
                  <VoteButton 
                    isUpVoter={true}
                    messages={messages}
                    setMessages={setMessages}
                    orderInChat={message.orderInChat}
                    chatId={nowChat}
                  />
                  <VoteButton 
                    isUpVoter={false}
                    messages={messages}
                    setMessages={setMessages}
                    orderInChat={message.orderInChat}
                    chatId={nowChat}
                  />
                </div> 
                :
                <div></div>
              }

            <div className="message-label">
                {calculateMessageLabel(message)}
            </div>

            </div>
            </>
        )    
    )
};

Message.propTypes = {
    message: PropTypes.object, 
    messages: PropTypes.array,
    setMessages: PropTypes.func,
    nowChat: PropTypes.number
};

export default Message;