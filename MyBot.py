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
        self.building_dropoff = False
        logging.info('size: {}x{}'.format(game.game_map.height, game.game_map.width))
        logging.info('Shipyard @ {}'.format(game.me.shipyard))
        self.ship_status = {}

        # Make sure you put variables above the run() function!
        self.run()
        
        
    def run(self):
        while True:
            # Get fresh values
            self.game.update_frame()
            self.me = game.me
            self.game_map = self.game.game_map
            self.players = self.game.players
            
            ships = self.me.get_ships()
            dropoffs = self.me.get_dropoffs()
            turns_left = constants.MAX_TURNS - self.game.turn_number
            command_queue = []
            logging.info('Number of dropoffs: {}'.format(len(dropoffs)))
            logging.info('Number of ships: {}'.format(len(ships)))
            logging.info('Halite amount: {}'.format(self.me.halite_amount))
            logging.info('Ship status: {}'.format(self.ship_status))

            for ship in ships:
                if ship.id not in self.ship_status:
                    self.ship_status[ship.id] = 'mining'
            
            # Se if we lost a ship
            ship_ids = [ship.id for ship in ships]
            for ship_id in self.ship_status:
                if ship_id not in ship_ids:
                    logging.info('We have lost {}'.format(ship_id))
            
            try:
                longest_distance_to_dropoff = (0,None)
                if len(ships) > 1:
                    for ship in ships:
                        ship_dist_to_dropoff = self.game_map.calculate_distance(ship.position, self.closest_dropoff(ship, dropoffs))
                        if ship_dist_to_dropoff > longest_distance_to_dropoff[0]:
                            longest_distance_to_dropoff = (ship_dist_to_dropoff,ship.id)
            except:
                raise
                logging.debug('No ships')
            


            # Check if we should build an dropoff
            if len(ships) > (len(dropoffs)+1)*8 and len(dropoffs) < 3:
                logging.info('Time to expand! {} ships:{} dropoffs:{} ratio:{}>{}'.
                             format(self.building_dropoff, len(ships), len(dropoffs),len(ships), (len(dropoffs)+1)*8))

                # Find best ship for expanding
                self.ship_status[longest_distance_to_dropoff[1]] = 'building_dropoff'
            
 
            # Itterate through each ship and decide what to do
            for ship in ships:
                logging.debug('\nProcessing ship:{} @ {} : {}'.format(ship.id, ship.position, self.ship_status[ship.id]))

                # Check if the ship need to return home
                if  turns_left < longest_distance_to_dropoff[0] * 1.5:
                    distance_to_dropoff = self.game_map.calculate_distance(ship.position, self.closest_dropoff(ship, dropoffs))
                    logging.debug('distance to home:{} - rounds left: {}'.format(distance_to_dropoff, turns_left))
                    self.ship_status[ship.id] = 'returning'
                    if distance_to_dropoff == 1:
                        command_queue.append(ship.move(self.game_map.get_unsafe_moves(ship.position, self.closest_dropoff(ship, dropoffs))[0]))
                    else:
                        command_queue.append(ship.move(self.game_map.naive_navigate(ship, self.closest_dropoff(ship, dropoffs))))

                    
                # Check if we can build the extra dropoff                          
                if self.ship_status[ship.id] == 'building_dropoff':
                    if self.me.halite_amount > 4000:
                        command_queue.append(ship.make_dropoff())
                        self.building_dropoff == False
                        logging.info('Ship:{} expanded @ {}'.format(ship.id, ship.position))
                    else:
                        self.ship_status[ship.id] = 'mining'
                        logging.info('{} could not expand at this time. Returning to mining'.format(ship.id))

                # Check if it should turn in cargo  
                if ship.halite_amount > 700 and self.ship_status[ship.id] not in ['returning','building_dropoff']:
                    command_queue.append(self.return_halite(ship, dropoffs))
                
                elif self.ship_status[ship.id] == 'mining':
                    command_queue.append(self.mine_halite(ship))

            # Check if we should build a new ship
            if ( len(ships) <= (len(dropoffs)+1)*8 and
                self.me.halite_amount >= constants.SHIP_COST and
                self.game_map[self.me.shipyard.position].occupied_by != self.me.id and
                not self.game_map[self.me.shipyard.position].is_occupied and turns_left > 50 and
                self.building_dropoff == False):
                
                command_queue.append(self.me.shipyard.spawn())
                logging.info('Building a new ship')

            
            logging.debug('command_queue:\n {}\n\n'.format(command_queue))
            game.end_turn(command_queue)


    def return_halite(self, ship, dropoffs):
        """ Method with logic for turning in halite"""
        logging.debug('***Returning***')
        move = Direction.Still
        closest_dropoff = self.closest_dropoff(ship, dropoffs)
        move = self.game_map.naive_navigate(ship, closest_dropoff)

        return ship.move(move)

    def mine_halite(self, ship):
        """ Method with logic for mining halite"""
        logging.debug('***Mining***')
        possible_moves=[]
        move = None
        
        # Check if we should stay put and mine.
        if self.game_map[ship.position].halite_amount > constants.MAX_HALITE/75:
            logging.debug('Mining at:{} with Halite:{}'.format(ship.position, self.game_map[ship.position].halite_amount))
            move = Direction.Still
            self.game_map[ship.position].mark_unsafe(ship)
        
        # Find next minable cell to move to
        else:
            for cardinal in ship.position.get_surrounding_cardinals():
                logging.debug('Cardinal: {} - Halite: {}'.format(cardinal, self.game_map[cardinal].halite_amount))
                if not self.game_map[cardinal].is_occupied and self.game_map[cardinal].halite_amount > constants.MAX_HALITE/75:
                    possible_moves.append(cardinal)
                    
            # Move towards the best candidate
            if len(possible_moves) > 0:
                max_halite = 0
                for m in possible_moves:
                    if self.game_map[m].halite_amount > max_halite:
                        max_halite = self.game_map[m].halite_amount
                        move = self.game_map.naive_navigate(ship, m)
                
                logging.debug('Moving: {}'.format(move))
           
            # If no mineable cell was found, move to a random cell. 
            if move == None:
                possible_moves = []
                size = 10
                for y in range(-1*size, size+1):
                    for x in range(-1*size, size+1):
                        test_position = ship.position + Position(x,y)
                        if self.game_map[test_position].halite_amount > constants.MAX_HALITE/75:
                            possible_moves.append(test_position)
                if len(possible_moves)>0:
                    move = self.game_map.naive_navigate(ship, random.choice(possible_moves))
                
            # If no move has been found, wait.
            if move == None:
                logging.info('No move found, waiting')
                move = Direction.Still
        next_position = ship.position.directional_offset(move)
        self.game_map[next_position].mark_unsafe(ship)
        logging.debug('next position {}'.format(next_position))
        return ship.move(move)

    def closest_dropoff(self, ship, dropoffs):
        shortest_distance = self.game_map.calculate_distance(ship.position, self.me.shipyard.position)
        closest_dropoff = self.me.shipyard.position
        for dropoff in dropoffs:
            distance_to_dropoff = self.game_map.calculate_distance(ship.position, dropoff.position)
            if distance_to_dropoff <= shortest_distance:
                shortest_distance = distance_to_dropoff
                closest_dropoff = dropoff.position
        return closest_dropoff
    
    def furthest_dropoff(self, ship, dropoffs):
        longest_distance = self.game_map.calculate_distance(ship.position, self.me.shipyard.position)
        furthest_dropoff = self.me.shipyard.position
        for dropoff in dropoffs:
            distance_to_dropoff = self.game_map.calculate_distance(ship.position, dropoff.position)
            if distance_to_dropoff >= longest_distance:
                longest_distance = distance_to_dropoff
                furthest_dropoff = dropoff.position
        return furthest_dropoff


if __name__ == '__main__':
    # --- Calculation heavy code below ---
    game = hlt.Game()
    # --- Calculation heavy code abowe ---

    game.ready("KuBot")
    logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))
    KuBot(game)