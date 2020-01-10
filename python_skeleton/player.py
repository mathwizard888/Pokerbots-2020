'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot
import random


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        self.VALUES = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        self.wins_dict = {v : 1 for v in self.VALUES}
        self.showdowns_dict = {v : 2 for v in self.VALUES}
        pass

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        #my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        #game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        #round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        #my_cards = round_state.hands[active]  # your cards
        #big_blind = bool(active)  # True if you are the big blind
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed
        if opp_cards != []:  # we have a showdown
            if my_delta > 0:  # we won
                self.wins_dict[my_cards[0][0]] += 1
                self.wins_dict[my_cards[1][0]] += 1
            self.showdowns_dict[my_cards[0][0]] += 1
            self.showdowns_dict[my_cards[1][0]] += 1
            if my_delta < 0:  # we lost
                self.wins_dict[opp_cards[0][0]] += 1
                self.wins_dict[opp_cards[1][0]] += 1
            self.showdowns_dict[opp_cards[0][0]] += 1
            self.showdowns_dict[opp_cards[1][0]] += 1
        pass

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        if legal_actions == {CheckAction}:
            return CheckAction()
        street = round_state.street  # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        pot_after_continue = my_contribution + opp_contribution + continue_cost
        pot_odds = continue_cost / pot_after_continue
        if RaiseAction in legal_actions:
            min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise
            min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
            max_cost = max_raise - my_pip  # the cost of a maximum bet/raise
            first_card_winrate = self.wins_dict[my_cards[0][0]] / self.showdowns_dict[my_cards[0][0]]
            second_card_winrate = self.wins_dict[my_cards[1][0]] / self.showdowns_dict[my_cards[1][0]]
            # for indexing
            winrates = [first_card_winrate, second_card_winrate]
            # count up how often our cards agree with the board cards
            agree_counts = [0, 0]
            for card in board_cards:
                # increase agree_counts each time values agree
                for i in range(2):
                    if my_cards[i][0] == card[0]:
                        agree_counts[i] += 1
            raise_amount = my_pip + continue_cost + int(0.75 * pot_after_continue)
            raise_amount = min(raise_amount, max_raise)
            raise_amount = max(raise_amount, min_raise)
            # TWO-PAIR OR BETTER
            if sum(agree_counts) >= 2:
                return RaiseAction(raise_amount)
            # ONE PAIR IN FIRST CARD
            if agree_counts[0] == 1:
                if random.random() < winrates[0]:
                    return RaiseAction(raise_amount)
                if CheckAction in legal_actions:
                    return CheckAction()
                if pot_odds < winrates[0]:
                    return CallAction()
            # ONE PAIR IN SECOND CARD
            if agree_counts[1] == 1:
                if random.random() < winrates[1]:
                    return RaiseAction(raise_amount)
                if CheckAction in legal_actions:
                    return CheckAction()
                if pot_odds < winrates[1]:
                    return CallAction()
            # POCKET PAIR
            if my_cards[0][0] == my_cards[1][0]:
                if random.random() < winrates[0]:
                    return RaiseAction(raise_amount)
                if CheckAction in legal_actions:
                    return CheckAction()
                if pot_odds < winrates[0]:
                    return CallAction()
            if first_card_winrate > 0.5 and second_card_winrate > 0.5 and street < 5:
                return RaiseAction(min_raise)
        if CheckAction in legal_actions:
            return CheckAction()
        return FoldAction()

if __name__ == '__main__':
    run_bot(Player(), parse_args())
