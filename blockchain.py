# External Imports
from functools import reduce
import hashlib as hl
from collections import OrderedDict
import json
import pickle

# Internal Imports
from hash_util import hash_string_256, hash_block

# The reward we give to miners (for creating a new block)
MINING_REWARD = 50

# Our starting block for the blockchain
GENESIS_BLOCK = {
    'previous_hash': '',
    'index': 0,
    'transactions': [],
    'proof': 100
}
# Initializing our blockchain with the genesis block
blockchain = [GENESIS_BLOCK]
# Unhandled transactions
open_transactions = []
# We are the owner of this blockchain node, hence this is our identifier
owner = 'Jorge'
# Registered participants: ourself + other people sending/receiving coins
participants = {'Jorge'}


def load_data():
    # with open('blockchain.p', mode='rb') as f:
    #     file_content = pickle.loads(f.read())

    #     global blockchain
    #     global open_transactions
    #     blockchain = file_content['chain']
    #     open_transactions = file_content['ot']
    
    # OrderedDict of blocks and transactions must be taken into account otherwise the POW check will error
    with open('data/blockchain.txt', mode='r') as f:
        file_content = f.readlines()
        global blockchain
        global open_transactions
        # loads method in json library used to deserialize the string to return python object
        # [:-1] removes \n character which isn't converted as it isn't valid json
        blockchain = json.loads(file_content[0][:-1])
        updated_blockchain = []
        for block in blockchain:
            updated_block = {
                'previous_hash': block['previous_hash'],
                'index': block['index'],
                'proof': block['proof'],
                'transactions': [OrderedDict([
                    ('sender', tx['sender']),
                    ('recipient', tx['recipient']),
                    ('amount', tx['amount'])
                ]) for tx in block['transactions']]
            }
            updated_blockchain.append(updated_block)
        blockchain = updated_blockchain
        # tx
        open_transactions = json.loads(file_content[1])
        updated_transactions = []
        for tx in open_transactions:
            updated_transaction = OrderedDict([
                ('sender', tx['sender']),
                ('recipient', tx['recipient']),
                ('amount', tx['amount'])
                ])
            updated_transactions.append(updated_transaction)
        open_transactions = updated_transactions


load_data()


def save_data():
    # Pickle version: requires mode='wb' for binary and file extension .p can be used
    # with open('blockchain.p', mode='wb') as f:
    #     save_data = {
    #         'chain': blockchain,
    #         'ot': open_transactions
    #     }
    #     f.write(pickle.dumps(save_data))
    # dumps method in json library used to convert python objects to strings
    with open('data/blockchain.txt', mode='w') as f:
        f.write(json.dumps(blockchain))
        f.write('\n')
        f.write(json.dumps(open_transactions))

def valid_proof(transactions, last_hash, proof):
    # Create a string with all the hash inputs
    guess = (str(transactions) + str(last_hash) + str(proof)).encode()
    print(guess)
    # Hash the string
    # IMPORTANT: This is NOT the same hash as will be stored in the previous_block
    guess_hash = hash_string_256(guess)
    print(guess_hash)
    # Only a hash (which is based on the above inputs) which meets the requirements is considered valid
    # In this case it is 2 leading zeroes
    return guess_hash[0:2] == '00'


def proof_of_work():
    last_block = blockchain[-1]
    last_hash = hash_block(last_block)
    proof = 0
    while not valid_proof(open_transactions, last_hash, proof):
        proof += 1
    return proof


def get_balance(participant):
    """ Calculate the amount of coins sent for the participant.

    Arguments:
        :participant: The person for whom to calculate the balance.
    """
    tx_sender = [[tx['amount'] for tx in block['transactions'] if tx['sender'] ==  participant] for block in blockchain]
    open_tx_sender = [tx['amount'] for tx in open_transactions if tx['sender'] == participant]
    # Add the amount spent in open transactions
    tx_sender.append(open_tx_sender)
    print(tx_sender)
    # Reduce function sums elements and passes into the tx_sum of the lambda arguments and continues to add the sum of tx_amt until empty. This replaces the for loop.
    amount_sent = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum, tx_sender, 0)
    # Calculate the amount of coins received for the participant
    tx_recipient = [[tx['amount'] for tx in block['transactions'] if tx['recipient'] ==  participant] for block in blockchain]
    # Reduce function sums elements and passes into the tx_sum of the lambda arguments and continues to add the sum of tx_amt until empty. This replaces the for loop.
    amount_received = reduce(lambda tx_sum, tx_amt: tx_sum + sum(tx_amt) if len(tx_amt) > 0 else tx_sum, tx_recipient, 0)
    # Calculate the balance of coins for the participant
    return amount_received - amount_sent


def get_last_blockchain_value():
    """ Returns the last value of the current blockchain """
    if len(blockchain) < 1:
        return None
    # Implicit else so no else line required
    return blockchain[-1]


def verify_transaction(transaction):
    sender_balance = get_balance(transaction['sender'])
    # Returns Boolean 
    return sender_balance >= transaction['amount']


# This function accepts two arguments.
# One required one (transaction_amount) and one optional one (last_transaction)
# The optional one is optional becuase it has a default value => [1]
def add_transaction(recipient, sender=owner, amount=1.0):
    """ Add a new transaction to the list of open transactions

    Arguments:
        :sender: The sender of the coins.
        :recipient: The recipient of the coins.
        :amount: The amount of coins sent with the transaction (default = 1.0)

    """
    # transaction = {
    #     'sender': sender,
    #     'recipient': recipient,
    #     'amount': amount
    # }
    # OrderedDict remembers the order in which its contents are added
    transaction = OrderedDict(
        [('sender', sender), ('recipient', recipient), ('amount', amount)]
        )
    # If the sender has sufficient balance to send the amount in the transaction, then add to the transaction to mempool
    if verify_transaction(transaction):
        open_transactions.append(transaction)
        # Add sender and recipient to list of blockchain participants
        participants.add(sender)
        participants.add(recipient)
        save_data()
        return True
    return False


def mine_block():
    """ Create a new block and add open transactions to it."""
    # Fetch the current last block of the blockchain
    last_block = blockchain[-1]
    # Hash the last block (=> to be able to compare it to the stroed has value)
    hashed_block = hash_block(last_block)
    # Calculate the proof of work
    proof = proof_of_work()
    # Miners should be rewarded, so let's create a reward transaction
    # reward_transaction = {
    #     'sender': 'MINING',
    #     'recipient': owner,
    #     'amount': MINING_REWARD
    # }
    # OrderedDict remembers the order in which its contents are added
    reward_transaction = OrderedDict(
        [('sender', 'MINING'), ('recipient', owner), ('amount', MINING_REWARD)]
        )
    # Copy the open transactions to a new List, instead of manipulating the original open_transactions
    copied_transactions = open_transactions[:]
    # Ensure we are manipulating a local list of transactions not a global one.
    # This ensures that if for some reason the mining should fail, we don't have extra reward transactions included across all nodes
    copied_transactions.append(reward_transaction)
    block = {
        'previous_hash': hashed_block,
        'index': len(blockchain),
        'transactions': copied_transactions,
        'proof': proof
    }
    blockchain.append(block)
    return True


def get_transaction_value():
    """ Returns the input of the user (a new transaction amount) as a float. """
    # Get the user input, transform it from a string to a float and store in
    tx_recipient = input('Enter the recipient of the transaction: ')
    tx_amount = float(input('Your transaction amount please: '))
    return (tx_recipient, tx_amount)


def get_user_choice():
    user_input = input('Your choice: ')
    return user_input


def print_blockchain_elements():
    """ Output all blocks of the blockchain. """
    # Output the blockchain list to the console
    for block in blockchain:
        print('Outputting Block')
        print(block)
    else:
        print('-' * 20)


def verify_chain():
    """ Verify the current blockchain and return True if its valid, False otherwise. """
    for (index, block) in enumerate(blockchain):
        if index == 0:
            # Genesis block cannot be modified since the hash is confirmed in the first block
            continue
        if block['previous_hash'] != hash_block(blockchain[index - 1]):
            return False
        # Use the transactions except the reward transaction by specifying :-1
        if not valid_proof(block['transactions'][:-1], block['previous_hash'], block['proof']):
            print('Proof of work is invalid')
            return False
    return True

# OLD - for loop for verifying transactions
# def verify_transactions():
#     is_valid = True
#     for tx in open_transactions:
#         if verify_transaction(tx):
#             is_valid = True
#         else:
#             is_valid = Falsee
#     return is_valid

def verify_transactions():
    """ all function used on Boolean verify_transaction(tx) so all tx must be verified as valid in order to return True """
    return all([verify_transaction(tx) for tx in open_transactions])

waiting_for_input = True

while waiting_for_input:
    print('Please choose')
    print('1: Add a new transaction value')
    print('2: Mine a new block')
    print('3: Output the blockchain values')
    print('4: Output the blockchain participants')
    print('5: Check transaction validity')
    print('h: Manipulate the chain')
    print('q: Quit')
    user_choice = get_user_choice()
    if user_choice == '1':
        tx_data= get_transaction_value()
        recipient, amount = tx_data
        # Add the transaction to the blockchain
        if add_transaction(recipient, amount=amount):
            print('Added transaction!')
        else:
            print('Transaction failed!')
        print(open_transactions)
    elif user_choice == '2':
        if mine_block():
            # Reset the open transactions back to empty (clear mempool)
            open_transactions = []
            # Call save data here not inside mine block so open transactions are empty in the file
            save_data()
    elif user_choice == '3':
        print_blockchain_elements()
    elif user_choice == '4':
        print(participants)
    elif user_choice == '5':
        if verify_transactions:
            print('All transactions are valid')
        else:
            print('There are invalid transactions')
    elif user_choice == 'h':
        # Make sure that you don't try to "hack" the blockchain if it's empty
        if len(blockchain) >= 1:
            blockchain[0] = {
                'previous_hash': '',
                'index': 0,
                'transactions': [{'sender': 'Chris', 'recipient': 'Jorge', 'amount': 100.0}]
            }
    elif user_choice == 'q':
        # This will lead the loop to exit because its running condition is no longer true
        waiting_for_input = False
    else:
        print('Input was invalid, please pick a value from the list')
    if not verify_chain():
        print_blockchain_elements()
        print('Invalid blockchain!')
        # Break out of the loop
        break
    print('Balance of {}: {:6.2f}'.format('Jorge', get_balance('Jorge')))
else:
    print('User left!')
      
print('Done!')