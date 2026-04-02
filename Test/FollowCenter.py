import os 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import threading
from queue import Queue
import cv2
import numpy as np
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import math

from Drivers.camera import Camera
from Drivers.Holder import Holder
from Algorithm.CenterGet import CenterGet
from Algorithm.PID import PID
from Algorithm.KalmanFilter2D import KalmanFilter2D


BASE_POINT = (291, 201)     # Laser point coordinates, 640*360 resolution only
max_points = 1000           # Maximum number of data points to display
data_queue = Queue()        # Data transfer queue

# Initialize data lists
error_history = []
pid_output_history = []
time_history = []

# Set up real-time plotting
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
line1, = ax1.plot([], [], 'r-', label='Error')
line2, = ax2.plot([], [], 'b-', label='PID Output')

ax1.set_ylabel('Error Value')
ax1.set_title('Real-time Error Curve')
ax1.legend()
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('PID Output')
ax2.set_title('Real-time PID Output')
ax2.legend()
fig.tight_layout()

# Plot update function
def update_plot(frame):
    # Get data from queue and update
    while not data_queue.empty():
        current_time, deta_y, pitch_value = data_queue.get()
        
        # Add new data
        time_history.append(current_time)
        error_history.append(deta_y)
        pid_output_history.append(pitch_value)
        
        # Remove old data
        while len(time_history) > max_points:
            time_history.pop(0)
            error_history.pop(0)
            pid_output_history.pop(0)
    
    # Handle empty data case
    if not time_history:
        return line1, line2
    
    # Update plot data
    line1.set_data(time_history, error_history)
    line2.set_data(time_history, pid_output_history)
    
    # Auto-adjust axis ranges
    ax1.relim()
    ax1.autoscale_view()
    ax2.relim()
    ax2.autoscale_view()
    
    return line1, line2

# Start animation
ani = FuncAnimation(fig, update_plot, interval=50, blit=True)

def main():
    cap = Camera()
    if not cap.open():
        print("Failed to open camera")
        return

    


    start_time = time.time()
    
    try:
        while True:
            loop_start = time.time()
            
            # Get image frame
            frame = cap.capture()
            if frame is None:
                print("Failed to get image frame")
                time.sleep(0.01)
                continue
            
            # Target detection
            center = CenterGet(frame)
            
            if center is not None:
                # Calculate deviations
                deta_x = -(BASE_POINT[0] - center[0]) * 0.001
                deta_y = +(BASE_POINT[1] - center[1]) * 0.001
                
                # PID control calculation
                yaw_value = yaw_pid.update(deta_x)
                pitch_value = pitch_pid.update(deta_y)
                
                # Control the holder
                holder.holder_move(yaw_value, pitch_value)
                # print(f"yaw: {holder.current_yaw_angle:.4f}, pitch: {holder.current_pitch_angle:.4f}")
                
                # Record current time and put in queue
                current_time = time.time() - start_time
                data_queue.put((current_time, deta_y, pitch_value))
            
            # Print debug information
            print(f'center: {center}')
            # print(f'loop time: {time.time() - loop_start:.4f}s')
            
            # Display image (optional)
            # if center is not None:
            #     cv2.circle(frame, center, 5, (0, 0, 255), -1)
            # cv2.imshow('frame', frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
                
    except KeyboardInterrupt:
        print("Program interrupted manually")
    finally:
        # Clean up resources
        cap.close()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    # Start main program
    main_thread = threading.Thread(target=main)
    main_thread.daemon = True
    main_thread.start()
    
    # Show plot window
    plt.show()
    
    # Wait for main program to finish
    main_thread.join()
    