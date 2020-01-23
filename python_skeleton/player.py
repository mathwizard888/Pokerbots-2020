'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot
import random
import eval7
from numpy.random import geometric


class Player(Bot):
    '''
    A pokerbot.
    '''

    def permute_values(self):
        '''
        Selects a value permutation for the whole game according the prior distribution.
        '''
        orig_perm = list(range(13))[::-1]
        prop_perm = []
        seed = geometric(p=0.25, size=13) - 1
        for s in seed:
            pop_i = len(orig_perm) - 1 - (s % len(orig_perm))
            prop_perm.append(orig_perm.pop(pop_i))
        return prop_perm

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        self.guar_win = False
        # particle filter
        values = list('23456789TJQKA')
        suits = list('cdhs')
        self.proposal_perms = []
        for j in range(20000):
            # proposal_perm is a list with entries from 0 to 12
            proposal_perm = self.permute_values()
            perm_dict = {}
            for i, v in enumerate(values):
                for s in suits:
                    card = v + s
                    permuted_i = proposal_perm[i]
                    permuted_v = values[permuted_i]
                    permuted_card = eval7.Card(permuted_v + s)
                    perm_dict[card] = permuted_card
            # we've gone through the whole deck
            self.proposal_perms.append(perm_dict)

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
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        #my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind
        if my_bankroll > (1001-round_num) + (1001-round_num-int(big_blind))//2:
            self.guar_win = True

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
        board_cards = previous_state.deck[:street]
        if opp_cards != []:  # we have a showdown
            # update particle filter
            new_perms = []
            for proposal_perm in self.proposal_perms:  # check if valid
                my_perm_cards = [proposal_perm[c] for c in my_cards]
                opp_perm_cards = [proposal_perm[c] for c in opp_cards]
                board_perm_cards = [proposal_perm[c] for c in board_cards]
                my_cards_available = my_perm_cards + board_perm_cards
                opp_cards_available = opp_perm_cards + board_perm_cards
                my_strength = eval7.evaluate(my_cards_available)
                opp_strength = eval7.evaluate(opp_cards_available)
                # consistent with my win
                if my_strength > opp_strength and my_delta > 0:
                   new_perms.append(proposal_perm)
                # consistent with opp win
                if my_strength < opp_strength and my_delta < 0:
                   new_perms.append(proposal_perm)
                # consistent with a tie
                if my_strength == opp_strength and my_delta == 0:
                   new_perms.append(proposal_perm)
            if len(new_perms) >= 10:
                self.proposal_perms = new_perms

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
        if self.guar_win:
            if CheckAction in legal_actions:
                return CheckAction()
            return FoldAction()
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

        # estimate card ranks
        valid_perms = 0
        my_ranks = [0,0]
        board_ranks = [0 for _ in range(street)]
        for perm in self.proposal_perms:
            valid_perms += 1
            for i in range(2):
                my_ranks[i] += perm[my_cards[i]].rank
            for i in range(street):
                board_ranks[i] += perm[board_cards[i]].rank
        for i in range(2):
            my_ranks[i] /= valid_perms
        my_rel_ranks = [0,0]
        for j in range(street):
            board_ranks[j] /= valid_perms
            for i in range(2):
                if board_ranks[j] <= my_ranks[i]:
                    my_rel_ranks[i] += 1

        strength = 0  # estimate hand strength
        
        # count up how often our cards agree with the board cards
        agree_counts = [0, 0]
        for card in board_cards:
            # increase agree_counts each time values agree
            for i in range(2):
                if my_cards[i][0] == card[0]:
                    agree_counts[i] += 1
                    strength += my_rel_ranks[i]/(2*street) + agree_counts[i]/20
        # pocket pair adjustment
        if my_cards[0][0] == my_cards[1][0]:
            if street > 0:
                strength += my_rel_ranks[0]/(2*street) + agree_counts[0]/5
            else:
                strength += (my_ranks[0]+1)/13

        # flush adjustment
        my_probs = [[0,0,0.1],[],[],[0,0,0,0.05,0.4,1],[0,0,0,0,0.2,1,1],[0,0,0,0,0,1,1,1]]
        opp_probs = [[0.05,0.3],[0,0.15,0.6],[0,0.05,0.2,1]]
        for suit in 'cdhs':
            my_count = 0
            board_count = 0
            for i in range(2):
                if my_cards[i][1] == suit:
                    my_count += 1
            for i in range(street):
                if board_cards[i][1] == suit:
                    board_count += 1
            # add for my flush
            strength += my_probs[street][my_count+board_count]
            # subtract for opp flush
            if street > 0 and board_count >= 2:
                strength -= opp_probs[street-3][board_count-2]

        # adjust based on game stage
        strength += sum(my_ranks)/(24*(street+2))

        # play based on strength
        if pot_odds < strength:
            if random.random() < strength:
                min_raise, max_raise = round_state.raise_bounds()  # the smallest and largest numbers of chips for a legal bet/raise
                min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
                max_cost = max_raise - my_pip  # the cost of a maximum bet/raise
                raise_amount = my_pip + continue_cost + int(0.75 * pot_after_continue)
                raise_amount = min(raise_amount, max_raise)
                raise_amount = max(raise_amount, min_raise)
                if RaiseAction in legal_actions:
                    return RaiseAction(raise_amount)
            if CallAction in legal_actions:
                return CallAction()
            
        if CheckAction in legal_actions:
            return CheckAction()
        return FoldAction()

if __name__ == '__main__':
    run_bot(Player(), parse_args())
