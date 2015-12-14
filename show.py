#!/usr/bin/python
# Copyright 2009 John Watlington
# Written by <wad@alum.mit.edu>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#  show
#  This is a script for walking through a MediaBook (either online or local),
#  and showing the media stored there.

import glob
import sys
import os
from stat import *
import pygame
import xoscreen

MAX_HISTORY_SIZE = 120

#  Photo book information
DEFAULT_BOOKS = os.path.join(os.environ["HOME"], "Pictures/*.jpg")

# sleep time between photo changes, in milliseconds
DEFAULT_SLEEP_TIME = 6000
DEFAULT_USAGE_TIME = 3000
SLEEP_TIME_INC = 1500
SHOW_DELAY = 1000

#  Text layout on the screen
SCREEN_X = 1200
SCREEN_Y = 900
FONT_SIZE = 36
MSG_FONT_SIZE = 72
TOP_MARGIN = 0
TEXT_BAR_TOP_Y = 868
TITLE_BAR_TOP_Y = 844
TITLE_BAR_LEFT_X = 10
DESC_BAR_TOP_Y = 870
DESC_BAR_LEFT_X = TITLE_BAR_LEFT_X
DATE_BAR_TOP_Y = TITLE_BAR_TOP_Y
DATE_BAR_RIGHT_X = SCREEN_X - TITLE_BAR_LEFT_X

MAX_IMAGE_HEIGHT = TEXT_BAR_TOP_Y - TOP_MARGIN
MAX_IMAGE_WIDTH = TEXT_BAR_TOP_Y * 4 / 3

#  The color of the text on the screen
title_color = (250, 250, 250)
date_color = title_color
desc_color = title_color
pause_color = (250, 250, 0)

#  Error messages (as photos)
DOWNLOAD_ERROR = 'error_download.png'
PARSE_ERROR = 'error_parse.png'
USAGE_ERROR = 'error_usage.png'
FOUND_ERROR = 'error_found.png'


class Photo:
    """  This is a photo.
         The initialization routine simply records the URL of
         the XHTML description of the photo.
         The load routine actually reads in the URL of the image,
         and the public data fields:

       title - The title of the page concatenated with the title of the photo
       desc - A description of the image
       date - The time and date the image was taken, in string form
       image_uri - URI of "normal" resolution image
       opener - either a file open or a URI open that knows the username/passwd
    """

    def __init__(self, image_uri):
        self.image_uri = image_uri
        self.desc = ''  # Just in case we don't find anything...
        self.date = ''
        self.title = ''
        self.start_of_page = False

    def show(self):
        """Opens and display the image file (downloading it first, if needed)
        """
        try:
            #  Load the image from the temporary filename
            image = pygame.image.load(self.image_uri)
        #  Handle errors at this stage by putting up an apology image,
        #  as it is too late to remove the image from the slide show...
        except IOError:
            self.tmp_file = DOWNLOAD_ERROR
            self.tmp_file_timestamp = pygame.time.get_ticks() - SHOW_DELAY
            self.download_time = 2000
            self.desc = self.image_uri

        #  Now calculate the size of the image on the screen
        imageRect = image.get_rect()
        #  scale_v uses vertical height as limit to scaling
        scale_v = float(MAX_IMAGE_HEIGHT) / float(imageRect.height)
        #  scale_h uses horizontal width as limit to scaling
        scale_h = float(MAX_IMAGE_WIDTH) / float(imageRect.width)
        #   We use whichever is smaller
        if scale_v > scale_h:
            scale = scale_h
        else:
            scale = scale_v

        #  Transform the image to a surface of that size
        newImage = pygame.transform.smoothscale(image,
                                                (int(
                                                    float(
                                                        imageRect.width
                                                    ) * scale),
                                                 int(
                                                    float(
                                                        imageRect.height
                                                    ) * scale)))

        #  Position the image on the screen
        newImageRect = newImage.get_rect()
        newImageRect.top = TOP_MARGIN
        newImageRect.centerx = screen.get_rect().centerx

        screen.fill(bgcolor)  # fill with a background color
        screen.blit(newImage, newImageRect)  # copy the scaled image

        return  # end of show method

    #   end of the Photo class
    #######################


class MediaArchive:
    """ This class implements a specialized generator with a history mechanism.
        Previous values may be requested, and the "current" value may
        be one that had previously been generated.
    """

    def __init__(self):
        #   This is the history buffer, a circular queue of MAX_HISTORY_SIZE
        self.history = []
        self.head = 0
        self.cur_photo = 0
        self.tail = 0

        #  Open the directory, and list the contents.
        filelist = sorted(glob.glob(DEFAULT_BOOKS))

        #  Init the history queue
        for filename in filelist:
            print filename
            self.history.append(Photo(filename))

        self.max_history = len(self.history)
        self.head = self.max_history - 1

    def next(self):
        """return the next photo in the queue
        """
        curr = self.cur_photo
        curr += 1
        if curr >= self.max_history:
            curr = 0
        self.cur_photo = curr
        return self.history[curr]

    def curr(self):
        """return the current value of the generator function
        """
        return self.history[self.cur_photo]

    def prev(self):
        """return the prev value of the generator function
        """
        if self.cur_photo == self.tail:
            #  Can't back up any more, return the oldest item
            return self.history[self.cur_photo]
        else:
            self.cur_photo -= 1
            if self.cur_photo < 0:
                self.cur_photo = self.max_history - 1
        return self.history[self.cur_photo]

    def _append_to_history(self, photo):
        #  Place the photo in the queue
        self.history[self.head] = photo

        #  Now increment the queue head pointer
        self.head += 1
        if self.head >= self.max_history:
            self.head = 0
        if self.head == self.tail:
            self.tail += 1
            if self.tail >= self.max_history:
                self.tail = 0
        return

    #   end of the MediaArchive class
    #######################


def print_centered_msg(message):
    screen.fill(bgcolor)  # fill with a background color
    font = pygame.font.Font(None, MSG_FONT_SIZE)
    msg_text = font.render(message, True, title_color)
    msg_textRect = msg_text.get_rect()
    msg_textRect.centerx = SCREEN_X / 2
    msg_textRect.centery = SCREEN_Y / 2
    screen.blit(msg_text, msg_textRect)
    pygame.display.flip()


def print_note(msg, msg_color=pause_color):
    font = pygame.font.Font(None, FONT_SIZE)
    msg_text = font.render(msg, True, msg_color)
    msg_textRect = msg_text.get_rect()
    msg_textRect.topright = (DATE_BAR_RIGHT_X, DESC_BAR_TOP_Y)
    screen.blit(msg_text, msg_textRect)


def print_paused():
    print_note('PAUSED')


#################################################################
#
#         Main procedure
#
size = SCREEN_X, SCREEN_Y   # XO screen is 1200 by 900
bgcolor = (0, 0, 0)           # grey background

pygame.init()
pygame.mouse.set_visible(False)   # turn off cursor

# create the pygame window at the desired size and return a Surface object for
# drawing in that window.
screen = pygame.display.set_mode(size)
print_centered_msg("Fetching photos...")

#  Initialize the MediaArchive by telling it what photo books to search
books = MediaArchive()
if len(books.history) != 0:
    books.curr().show()  # Show the "first" photo
    pygame.display.flip()

#  Set up the timers for the display loop
sleep_time = DEFAULT_SLEEP_TIME
next_time = pygame.time.get_ticks() + sleep_time
blanked_out = False
old_brightness = 50  # this value not used
paused = False
changed = False
next_photo = None

#  And enter the activity event handling loop
while True:
    for event in pygame.event.get():
        #   QUIT          (Q, ESC)
        if event.type == pygame.QUIT:
            if blanked_out:
                xoscreen.set_display_brightness(old_brightness)
            sys.exit()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                sys.exit()

        if len(books.history) == 0:
            break

        if blanked_out and event.type == pygame.KEYDOWN:
            blanked_out = False
            xoscreen.set_display_brightness(old_brightness)

        #   PAUSE/PLAY    ( SPACE, P )
        elif event.type == pygame.KEYDOWN:
            if (event.key == pygame.K_SPACE) or (event.key == pygame.K_p):
                if paused:
                    paused = False
                else:
                    paused = True

                    books.curr().show()

                    print_paused()
                    pygame.display.flip()

        #   SKIP TO NEXT PICTURE  ( -> )
            elif event.key == pygame.K_RIGHT:
                next_photo = books.next()
                changed = True

        #   SKIP TO PREV PICTURE  ( <- )
            elif event.key == pygame.K_LEFT:
                next_photo = books.prev()
                changed = True

        #   INCREASE FRAME FREQ ( >, . )
            elif (event.key == pygame.K_PERIOD) or \
                 (event.key == pygame.K_GREATER):
                if sleep_time > SLEEP_TIME_INC * 20:
                    sleep_time -= SLEEP_TIME_INC * 10
                elif sleep_time > SLEEP_TIME_INC:
                    sleep_time -= SLEEP_TIME_INC
                books.curr().show()
                pygame.display.flip()

        #   DECREASE FRAME FREQ ( <, , )
            elif (event.key == pygame.K_COMMA) or (event.key == pygame.K_LESS):
                if sleep_time < SLEEP_TIME_INC * 10:
                    sleep_time += SLEEP_TIME_INC
                else:
                    sleep_time += SLEEP_TIME_INC * 10
                books.curr().show()
                pygame.display.flip()

        #   BLANK DISPLAY   ( B, S )
            elif (event.key == pygame.K_b) or (event.key == pygame.K_s):
                blanked_out = 1
                old_brightness = xoscreen.get_display_brightness()
                xoscreen.set_display_brightness(0)

        #   USAGE INFORMATION (on any other key)
            else:
                screen.fill(bgcolor)  # fill with a background color
                image = pygame.image.load(USAGE_ERROR)
                ImageRect = image.get_rect()
                ImageRect.top = TOP_MARGIN
                ImageRect.centerx = screen.get_rect().centerx
                screen.blit(image, ImageRect)
                pygame.display.flip()
                next_time = pygame.time.get_ticks() + DEFAULT_USAGE_TIME

    if len(books.history) == 0:
        screen.fill(bgcolor)  # fill with a background color
        image = pygame.image.load(FOUND_ERROR)
        ImageRect = image.get_rect()
        ImageRect.top = TOP_MARGIN
        ImageRect.centerx = screen.get_rect().centerx
        screen.blit(image, ImageRect)
        pygame.display.flip()
        next_time = pygame.time.get_ticks() + DEFAULT_USAGE_TIME
        continue

    #  If the user has pressed a key and triggered a photo change
    if changed:
        next_photo.show()
        if paused:
            print_paused()
        pygame.display.flip()
        next_time = pygame.time.get_ticks() + sleep_time
        changed = False

    #  Or, are we unpaused and it is time to change the photo
    elif not paused and not blanked_out and \
            (next_time < pygame.time.get_ticks()):
        next_photo = books.next()
        next_photo.show()
        pygame.display.flip()
        next_time = pygame.time.get_ticks() + sleep_time
