document.addEventListener('DOMContentLoaded', () => {
    console.log('main.js loaded.');

    /**
     * Отображает кастомное модальное окно подтверждения.
     * @param {string} message - Сообщение для отображения в диалоге.
     * @returns {Promise<boolean>} Промис, который разрешается в true, если пользователь нажал "Подтвердить", иначе false.
     */
    window.showCustomConfirmDialog = function(message) {
        return new Promise(resolve => {
            const modalOverlay = document.createElement('div');
            modalOverlay.classList.add('custom-modal-overlay');

            const modal = document.createElement('div');
            modal.classList.add('custom-modal');

            const messageParagraph = document.createElement('p');
            messageParagraph.textContent = message;

            const buttonContainer = document.createElement('div');
            buttonContainer.classList.add('custom-modal-buttons');

            const confirmButton = document.createElement('button');
            confirmButton.classList.add('confirm-btn');
            confirmButton.textContent = 'Подтвердить';

            const cancelButton = document.createElement('button');
            cancelButton.classList.add('cancel-btn');
            cancelButton.textContent = 'Отмена';

            buttonContainer.appendChild(cancelButton);
            buttonContainer.appendChild(confirmButton);

            modal.appendChild(messageParagraph);
            modal.appendChild(buttonContainer);

            modalOverlay.appendChild(modal);

            document.body.appendChild(modalOverlay);

            confirmButton.addEventListener('click', () => {
                modalOverlay.remove();
                resolve(true);
            });

            cancelButton.addEventListener('click', () => {
                modalOverlay.remove();
                resolve(false);
            });

            modalOverlay.addEventListener('click', (e) => {
                if (e.target === modalOverlay) {
                    modalOverlay.remove();
                    resolve(false);
                }
            });
        });
    };

    /**
     * Отображает временное flash-сообщение на странице.
     * @param {string} message - Текст сообщения.
     * @param {string} type - Тип сообщения (например, 'success', 'danger', 'warning', 'info').
     */
    window.flashMessage = function(message, type) {
        console.log(`Flash message: [${type}] ${message}`);
        const container = document.querySelector('.container');
        if (!container) {
            console.warn('Cannot find .container element for flash messages.');
            return;
        }

        let flashMessagesContainer = document.querySelector('.flash-messages');
        if (!flashMessagesContainer) {
            flashMessagesContainer = document.createElement('div');
            flashMessagesContainer.classList.add('flash-messages');
            // Вставляем контейнер для flash-сообщений после навигационной панели, но до основного контента
            const navbar = document.querySelector('.navbar');
            if (navbar && navbar.nextElementSibling) {
                navbar.parentNode.insertBefore(flashMessagesContainer, navbar.nextElementSibling);
            } else {
                container.insertBefore(flashMessagesContainer, container.firstChild);
            }
        }

        const alertDiv = document.createElement('div');
        alertDiv.classList.add('alert', `alert-${type}`);
        alertDiv.textContent = message;
        
        flashMessagesContainer.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.remove();
        }, 5000); // Сообщение исчезнет через 5 секунд
    };

    // Проверяем, есть ли flash-сообщения из Flask на странице и отображаем их
    const flaskFlashedMessages = JSON.parse(document.getElementById('flashed-messages-data')?.textContent || '[]');
    if (flaskFlashedMessages && flaskFlashedMessages.length > 0) {
        flaskFlashedMessages.forEach(msg => {
            flashMessage(msg.message, msg.category);
        });
    }

    // Добавляем стили для модального окна в DOM
    const style = document.createElement('style');
    style.innerHTML = `
        .custom-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .custom-modal {
            background-color: #fff;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            text-align: center;
            max-width: 400px;
            width: 90%;
        }
        .custom-modal p {
            margin-bottom: 20px;
            font-size: 1.1em;
            color: #333;
        }
        .custom-modal-buttons {
            display: flex;
            justify-content: center;
            gap: 15px;
        }
        .custom-modal-buttons button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 1em;
            cursor: pointer;
            transition: background-color 0.2s ease-in-out;
        }
        .custom-modal-buttons .confirm-btn {
            background-color: #007aff;
            color: white;
        }
        .custom-modal-buttons .confirm-btn:hover {
            background-color: #0056b3;
        }
        .custom-modal-buttons .cancel-btn {
            background-color: #e0e0e0;
            color: #333;
        }
        .custom-modal-buttons .cancel-btn:hover {
            background-color: #d0d0d0;
        }
    `;
    document.head.appendChild(style);
});
