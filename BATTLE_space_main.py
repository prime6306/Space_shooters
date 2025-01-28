import pygame
import random
import math
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
pygame.init()
from pygame import mixer
screen = pygame.display.set_mode((710,1530))



# game over
over = pygame.font.Font('freesansbold.ttf', 60)
def g_over():
	game = over.render('GAME OVER', True,(50,170,32))
	screen.blit(game,(180,380))
	
#creating buttons
def buttons(button_x,button_y,msg):
	button = pygame.image.load('button.png')
	screen.blit(button,(button_x,button_y))
	st = pygame.font.Font('freesansbold.ttf', 124) 
	text = st.render(msg,True,(111,250,111))
	screen.blit(text,(button_x+132,button_y+200))
	pygame.display.update() 

#game intro
def game_intro():
	intro = True 
	introback = pygame.image.load('introbackground.png')
	screen.blit(introback,(0,0))
	while intro:
		buttons(50,200,'PLAY')
		buttons(50,800,'QUIT')
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				intro = False
			pos = pygame.mouse.get_pos()
			if (pos[0]>50 and pos[0]<50+500) and (pos[1]>350 and pos[1]<=200+350):
				game_loop()
			if (pos[0]>50 and pos[0]<50+500) and (pos[1]>950 and pos[1]<=800+350):
				pygame.quit()
				quit()
				

		
	#	pygame.display.update() 
		
#game loop
def game_loop():
	background = pygame.image.load('background.png')
	#sounds
	mixer.music.load('background.mp3')
	mixer.music.play(-1)

#backbutton
	def button():
		backbutton = pygame.image.load('backbutton.png')
		screen.blit(backbutton,(600,6))
	
#creating player 
	player = pygame.image.load('spaceship.png')
	def player_loc(player_x):
		screen.blit(player,(player_x, 1160)) 
#highscore
	
	
#creating enemy
	enemy = []
	enemy_x = []
	enemy_y = []
	enemy_x_change = []
	enemy_y_change = []
	enemy_number = 6
	for i in range(enemy_number):
		enemy.append(pygame.image.load('enemy.png'))
		enemy_x.append(random.randint(0,650))
		enemy_y.append(random.randint(70,250))
		enemy_x_change.append(5)
		enemy_y_change.append(35)	
	def enemy_loc(enemy_x_change,enemy_y_change,i):
		screen.blit(enemy[i],(enemy_x[i],enemy_y[i]))
		
#enemy attack
	attack = pygame.image.load('enemybullet.png')
	attack_x = random.randint(0,650)
	attack_y = random.randint(70,90)
	attack_y_change = 12
	def attack_loc(attack_x,attack_y):
		screen.blit(attack,(attack_x,attack_y))
		
#enemy attack
	attack1 = pygame.image.load('enemybullet.png')
	attack1_x = random.randint(0,650)
	attack1_y = random.randint(70,90)
	attack1_y_change = 12
	def attack1_loc(attack1_x,attack1_y):
		screen.blit(attack1,(attack1_x,attack1_y))
		
#creating bullet
	bullet = pygame.image.load('bullet.png')
	bpos = pygame.mouse.get_pos()
	bullet_x = bpos[0]
	bullet_y = 1160
	bullet_y_change = -15
	bullet_state = 'ready'
	def bullet_loc(bullet_x_change,bullet_y_change):
		global bullet_state
		bullet_state = 'fire'
		screen.blit(bullet,(bullet_x_change+48,bullet_y_change+13))
		
# collision
	def collision(enemy_x,enemy_y,bullet_x,bullet_y,i):
		distance = math.sqrt(((enemy_x - bullet_x)**2)+((bullet_y - enemy_y)**2))
		return distance < i

#FPS settings	
	clock = pygame.time.Clock()
	FPS = 60
	run = True

# score calculation	
	score = 0
	font = pygame.font.Font('freesansbold.ttf', 36)
	def score_loc():
		scoref = font.render('score :- ' + str(score), True,(0,250,5))
		screen.blit(scoref,(10,13))
		
		
# boss fight
	boss = pygame.image.load('boss.png')
	boss_x = 400
	boss_y = 0
	boss_x_change = 2
	boss_y_change = 28
	boss_score = 15
	def boss_loc(boss_x_change,boss_y_change):
		screen.blit(boss,(boss_x_change,boss_y_change))
				
			
#while loop					
	while run:
		clock.tick(FPS)
		button()
		back_pos = pygame.mouse.get_pos()	
		if (back_pos[0]>580 and back_pos[0]<650) and (back_pos[1]>0 and back_pos[1]<50):
			game_intro()
			

#event loop	
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				run = False
		pos = pygame.mouse.get_pos()
		pos_x = pos[0]
		pos_y = 1160
		
#player control		
		if pos[0]<25:
			pos_x = 25
		if pos[0]>575:
			pos_x = 575
		player_loc(pos_x)
#boss
		if score == 50:
			enemy_number = 3
			fo = pygame.font.Font('freesansbold.ttf', 66)
			incoming = fo.render('BOSS FIGHT!!',True,(200,40,30))
				
			screen.blit(incoming,(180,380))
		if boss_score != 0 and score > 50 and boss_score >0:
			boss_x += boss_x_change
			if boss_x <= 0:
				boss_x_change = 2
				boss_y += boss_y_change
			elif boss_x >= 650:
				boss_x_change = -2
				boss_y += boss_y_change
			boss_loc(boss_x,boss_y)
#boss colision
			if boss_y > 50:
				boss_check = collision(boss_x,boss_y,bullet_x,bullet_y,90)
				if boss_check:
					s1 = mixer.Sound('bulletsound.mp3')
					s1.play()
					bullet_y = 1160+13
					bullet_state = 'ready'		
					bullet_x = pos_x
					boss_score -= 1	
		
		if boss_score == 0:
			score += 20
			boss_score = -1
			enemy_number += 3
		
# bullet control
		if bullet_state == 'ready':
			
			bullet_y += bullet_y_change
			
			bullet_loc(bullet_x,bullet_y)		
		if bullet_y <= 0:
			bullet_y = 1160+13
			bullet_state = 'ready'
			bullet_x = pos_x	
					
#attack control
		attack_y += attack_y_change
		attack_loc(attack_x,attack_y)
		if attack_y >= 1160:
			attack_x = random.randint(0,650)
			attack_y = random.randint(70,250)
		attack_check = collision(attack_x,attack_y+10,pos_x+32,pos_y,70)
		if attack_check:
			for j in range(enemy_number):
				enemy_y[j] = 5000
			
			g_over()
			boss_y = 5000
			
		attack1_y += attack1_y_change
		attack1_loc(attack1_x,attack1_y)
		if attack1_y >= 1160:
			attack1_x = random.randint(0,650)
			attack1_y = random.randint(70,250)
		attack1_check = collision(attack1_x,attack1_y,pos_x+35,pos_y,70)
		if attack1_check:
			for j in range(enemy_number):
				enemy_y[j] = 5000
			
			g_over()
			boss_y = 5000
			
		if boss_y >= 1040:
			for j in range(enemy_number):
				enemy_y[j] = 5000
			
			g_over()
			boss_y = 5000
		
				
#enemy control
		for i in range(enemy_number):
			if enemy_y[i] > 1100:
				for j in range(enemy_number):
					enemy_y[j] = 5000
			
				g_over()
				
	
		
			enemy_x[i] += enemy_x_change[i]
			if enemy_x[i] <= 0:
				enemy_x_change[i] = 5
				enemy_y[i] += enemy_y_change[i]
			elif enemy_x[i] >= 650:
				enemy_x_change[i] = -5
				enemy_y[i] += enemy_y_change[i]
		
# collision			
			collision_check = collision(enemy_x[i],enemy_y[i],bullet_x,bullet_y,50)
			if collision_check:
				s1 = mixer.Sound('bulletsound.mp3')
				s1.play()
				bullet_y = 1160+13
				bullet_state = 'ready'
				
				bullet_x = pos_x
				score += 1
				enemy_x[i] = random.randint(0,650)
				enemy_y[i] = random.randint(70,250)
			enemy_loc(enemy_x[i],enemy_y[i],i)
			
		
		score_loc()
		pygame.display.update() 
		screen.fill((11,45,35))
		screen.blit(background,(0,0))
			
game_intro()		
	
	
