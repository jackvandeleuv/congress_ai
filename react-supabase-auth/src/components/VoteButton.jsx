import UpvoteSVG from '../assets/upvote.svg';
import DownvoteSVG from '../assets/downvote.svg';
import UpvoteActiveSVG from '../assets/upvote-active.svg';
import DownvoteActiveSVG from '../assets/downvote-active.svg';
import PropTypes from 'prop-types';
import { useState, useEffect, useCallback } from 'react';
import { supabase } from "../supabase/client";
import './Components.css';


const VoteButton = ({ isUpVoter, messages, setMessages, orderInChat, chatId }) => {
    const [isActive, setIsActive] = useState(false);


    const findMatchingMessageIndex = useCallback(() => {    
        let idx = -1;
        for (let i = 0; i < messages.length; i++) {
            if (messages[i].orderInChat === orderInChat) { 
                idx = i;
                break; 
            }
        }

        if (idx === -1) { throw new Error('VoteButton could not find cooresponding message.'); }
        if (![-1, 0, 1, null].includes(messages[idx].rating)) { throw new Error('VoteButton got unexpected rating value.'); }

        return idx;
    }, [messages, orderInChat])
    

    useEffect(() => {
        const idx = findMatchingMessageIndex();
        const assignedRating = isUpVoter ? 1 : -1;
        setIsActive(messages[idx].rating === assignedRating);
    }, [messages, orderInChat, isUpVoter, findMatchingMessageIndex]);


    const handleClick = () => {
        const idx = findMatchingMessageIndex();
        const updatedMessage = {...messages[idx]}

        if (isActive) { 
            updatedMessage.rating = 0;  // Since we are unclicking, set rating back to default.
        } else { 
            updatedMessage.rating = isUpVoter ? 1 : -1;  // Set rating depending on what type of button we are.
        }
        setMessages(prev => prev.map(message => message.orderInChat === orderInChat ? updatedMessage : message));

        postRating(updatedMessage.orderInChat, updatedMessage.rating);  // Send updated rating to the database
    };


    const postRating = async (orderInChat, rating) => {
        const { error } = await supabase
            .from('messages')
            .update({ 'rating': rating })
            .match({'order_in_chat': orderInChat, 'chats_id': chatId})

        if (error) { console.error(error); }
    };


    return (
        <img 
            src={isUpVoter ? (isActive ? UpvoteActiveSVG : UpvoteSVG) : (isActive ? DownvoteActiveSVG : DownvoteSVG)} 
            alt={isUpVoter ? "Upvote" : "Downvote"}
            onClick={handleClick} 
            className={"vote-button"}
        />
    )
};

VoteButton.propTypes = {
    isUpVoter: PropTypes.bool, 
    messages: PropTypes.array,
    setMessages: PropTypes.func,
    orderInChat: PropTypes.number,
    chatId: PropTypes.number,
    sessionToken: PropTypes.string
  };

export default VoteButton;