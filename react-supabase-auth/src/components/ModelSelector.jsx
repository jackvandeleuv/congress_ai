import PropTypes from 'prop-types';
import './Components.css';

const ModelSelector = ({ selectedModel, setSelectedModel }) => {
    const handleOptionChange = (option) => {
        setSelectedModel(option);
    };


    return (
        <div className='model-selector-container'>
            <button 
                onClick={() => handleOptionChange('gpt-3.5-turbo-1106')}
                className={selectedModel === 'gpt-3.5-turbo-1106' ? 'selected-model' : 'not-selected-model'}
            >
                gpt-3.5-turbo-1106
            </button>
            <button
                onClick={() => handleOptionChange('gpt-4-1106-preview')}
                className={selectedModel === 'gpt-4-1106-preview' ? 'selected-model' : 'not-selected-model'}
            >
                gpt-4-1106-preview
            </button>
        </div>
    );
};


ModelSelector.propTypes = {
    selectedModel: PropTypes.string, 
    setSelectedModel: PropTypes.func,
};

export default ModelSelector;