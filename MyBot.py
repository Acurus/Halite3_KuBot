#!/usr/bin/env python3
# Python 3.6

import logging
import random

import hlt
from hlt import constants
from hlt.positionals import Direction, Position

class KuBot():
    def __init__(self, game):
        logging.info('turns: {}'.format(constants.MAX_TURNS))
        self.game = game
        logging.info('size: {}x{}'.format(game.game_map.height, game.game_map.width))
        self.build = {'worker':35,'attacker':1}
        self.ship_types = {} # what the ships are doing
        self.waiting = {} # How long a ship has been waiting in one spot
        self.run()
        
    
    def run(self):
        while True:
            # Get fresh values
            self.game.update_frame()
            self.me = game.me
            self.game_map = self.game.game_map
            self.players = self.game.players
            ships = self.me.get_ships()
            turns_left = constants.MAX_TURNS - self.game.turn_number
            command_queue = []
            longest_distance_to_home = 0

            # Check if we lost any ships last round
            ship_ids = [ship.id for ship in ships]
            for ship in self.ship_types:
                if ship not in ship_ids:
                    self.ship_types[ship] = 'dead'
                    logging.info('****Ship id{} Died****'.format(ship))
                    #del self.ship_types[ship]

                try:
                    longest_distance_to_home = max([self.game_map.calculate_distance(ship.position, self.me.shipyard.position) for ship in ships])
                except:
                    logging.debug('No ships')
            # Itterate through each ship and decide what to do
            for ship in ships:
                logging.debug('\nProcessing ship:{} @ {}'.format(ship.id, ship.position))

                # Check if the ship need to return home
                if  turns_left < longest_distance_to_home * 1.5:
                    distance_to_home = self.game_map.calculate_distance(ship.position, self.me.shipyard.position)
                    logging.debug('distance to home:{} - rounds left: {}'.format(distance_to_home, turns_left))
                    self.ship_types[ship.id] = 'returning'
                    if distance_to_home == 1:
                        command_queue.append(ship.move(self.game_map.get_unsafe_moves(ship.position, self.me.shipyard.position)[0]))
                    else:
                        command_queue.append(ship.move(self.game_map.naive_navigate(ship, self.me.shipyard.position)))

                    

                # Add ship to ship_types dictionary if it's not there and assign role.
                if ship.id not in self.ship_types:
                    if sum(value == 'worker' for value in self.ship_types.values()) < self.build['worker']:
                        self.ship_types[ship.id] = 'worker'
                    else:
                        self.ship_types[ship.id] = 'attacker'

                # Check if it should turn in cargo                            
                if ship.halite_amount > 700 and self.ship_types[ship.id] != 'returning':
                    command_queue.append(self.return_halite(ship))
                
                # Check role and decide next move
                elif self.ship_types[ship.id] == 'worker':
                    command_queue.append(self.mine_halite(ship))
                
                elif self.ship_types[ship.id] == 'attacker':
                    command_queue.append(self.attack(ship))
            
            # Check if we should build a new ship
            if ( len(ships) <= game.game_map.height and
                self.me.halite_amount >= constants.SHIP_COST and
                self.game_map[self.me.shipyard].occupied_by != self.me.id and
                not self.game_map[self.me.shipyard].is_occupied and turns_left > 50):

                command_queue.append(self.me.shipyard.spawn())
            
            logging.debug('command_queue:\n {}\n\n'.format(command_queue))
            logging.debug('waiting: {}'.format(self.waiting))
            game.end_turn(command_queue)

    def return_halite(self, ship):
        """ Method with logic for turning in halite"""
        logging.debug('***Returning***')
        move = Direction.Still
        
        # Find the way to the dropoff
        for direction in self.game_map.get_unsafe_moves(ship.position, self.me.shipyard.position):
            target_pos = ship.position.directional_offset(direction)
        if not self.game_map[target_pos].occupied_by == self.me.id:
            move = direction
        
        
        next_position = ship.position.directional_offset(move)
        self.game_map[next_position].mark_unsafe(ship)
        return ship.move(move)

    def mine_halite(self, ship):
        """ Method with logic for mining halite"""
        logging.debug('***Mining***')
        possible_moves=[]
        move = None
        
        # Check if we should stay put and mine.
        if self.game_map[ship.position].halite_amount > constants.MAX_HALITE/100:
            logging.debug('Mining at:{} with Halite:{}'.format(ship.position, self.game_map[ship.position].halite_amount))
            move = Direction.Still
            self.game_map[ship.position].mark_unsafe(ship)
        
        # Find next minable cell to move to
        else:
            for cardinal in ship.position.get_surrounding_cardinals():
                logging.debug('Cardinal: {} - Halite: {}'.format(cardinal, self.game_map[cardinal].halite_amount))
                if not self.game_map[cardinal].is_occupied and self.game_map[cardinal].halite_amount > constants.MAX_HALITE/100:
                    possible_moves.append(self.game_map.naive_navigate(ship, cardinal))
                    
            # Move towards a random candidate
            if len(possible_moves) > 0:
                move = random.choice(possible_moves)
                logging.debug('Moving: {}'.format(move))
           
            # If no mineable cell was found, move to a random cell. 
            if move == None:
                for cardinal in ship.position.get_surrounding_cardinals():
                    if not self.game_map[cardinal].is_occupied:
                        possible_moves.append(self.game_map.naive_navigate(ship, cardinal))
                    
                # Move towards a random candidate
                if len(possible_moves) > 0:
                    move = random.choice(possible_moves)
                    logging.debug('No halite found, moving to: {}'.format(move))
                        
            # If no move has been found, wait.
            if move == None:
                move = Direction.Still
        next_position = ship.position.directional_offset(move)
        self.game_map[next_position].mark_unsafe(ship)
        logging.debug('next position {}'.format(next_position))
        return ship.move(move)

    def attack(self, ship):
        """ Method for attacking the enemy"""
        logging.debug('***Attack***')
        move = Direction.Still
        
        # Find an enemy player
        for player in self.players:
            if player == self.me.id:
                continue
            
            enemy_shipyard = self.players[player].shipyard.position
            # Find a way towards the enemy shipyard without colliding with a friendly.
            for direction in self.game_map.get_unsafe_moves(ship.position, enemy_shipyard):
                target_pos = ship.position.directional_offset(direction)
                if not self.game_map[target_pos].occupied_by == self.me.id:
                    move = direction                    
            
            next_position = ship.position.directional_offset(move)
            self.game_map[next_position].mark_unsafe(ship)
            return ship.move(move)

if __name__ == '__main__':
    # --- Calculation heavy code below ---
    game = hlt.Game()
    # --- Calculation heavy code abowe ---

    game.ready("KuBot")
    logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))
    KuBot(game)