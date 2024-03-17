from django.shortcuts import render,redirect
import os
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import cv2
import numpy as np
import zipfile
from datetime import datetime
from django.http import HttpResponse

def Index(request):
    question = [1, 2, 3, 4, 5]  
    if request.method == "POST":
        upload_folder = os.path.join(settings.MEDIA_ROOT, 'OMR_Sheets')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        images = request.FILES.getlist("images")
        for image in images:
            with open(os.path.join(upload_folder, image.name), 'wb') as f:
                for chunk in image.chunks():
                    f.write(chunk)
        answers = []
        for i in question:
            answers.append(request.POST.get("answer" + str(i)))

        predictionFun(answers)
        
        # Create folder and zip file with current date and time
        current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        folder_name = f'OMR_Answers_{current_datetime}'
        zip_file_name = f'OMR_Answers_{current_datetime}.zip'
        folder_path = os.path.join(settings.MEDIA_ROOT, folder_name)
        zip_file_path = os.path.join(settings.MEDIA_ROOT, zip_file_name)
        
        # Move the processed images to the named folder
        os.rename(os.path.join(settings.MEDIA_ROOT, 'OMR_Answers'), folder_path)
        
        # Compress the named folder into a zip file
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))

        # Open the zip file in binary mode and serve it as a response
        with open(zip_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{zip_file_name}"'
            # Redirect back to the index page after downloading the zip file
            return response
    else:
        return render(request, "index.html", {"q": question})
    

def predictionFun(answers):
    negative_marking = True
    questions = 5
    choices = 5

    # input and output folder paths
    input_folder_path = './OMR_Sheets'
    output_folder_path = './OMR_Answers'

    # Ensure the folder path exists
    if os.path.exists(input_folder_path):
        # Create the output folder if it doesn't exist
        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)

        # Loop through all images in the folder
        for filename in os.listdir(input_folder_path):
            # Check if the file is an image (you may want to add more file type checks if needed)
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Construct the full path to the image
                image_path = os.path.join(input_folder_path, filename)

                # calling the function in main to get the answers marked in the image
                img, score = get_answers(image_path, answers, negative_marking, questions, choices)

                new_filename = f"{os.path.splitext(filename)[0]}_{score}%{os.path.splitext(filename)[1]}"

                # Construct the full path to the output image
                output_image_path = os.path.join(output_folder_path, new_filename)

                # Save the processed image using cv2.imwrite
                cv2.imwrite(output_image_path, img)
            else:
                print(f"Skipped non-image file: {filename}")

    else:
        print(f"The folder path '{input_folder_path}' does not exist.")


def get_answers(path, answers, negative_marking, questions, choices):
    widthImg = 700
    heightImg = 700

    # converting answers to indexes. calling the function from utils file
    answers = convertAnswers(answers)

    while True:
        img = cv2.imread(path)

        img = cv2.resize(img, (widthImg, heightImg))
        imgContours = img.copy()
        finalImg = img.copy()
        imgBiggestContours = img.copy()
        imgGradeContours = img.copy()

        ## image preprocessing
        # first converting the image to canny to detect the rectangles in the picture 
        # were big rectangle will have the OMR bubbles and the small rectangle will be the grade marking box.
        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # adding blur
        imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
        # detecting edges
        imgCanny = cv2.Canny(imgBlur, 10, 50)

        try:
            # then we find out the rectangles in the picture and finding out the corner points.
            contours, heirarchy = cv2.findContours(imgCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(imgContours, contours, -1, (0, 255, 0), 10)

            # finding rectangles. calling the function from the utils file
            rectangleContours = rectContour(contours)
            # we are getting every points of the pixels. we want the corner points only
            biggestContour = getCornerPoints(rectangleContours[0])
            gradePoints = getCornerPoints(rectangleContours[1])    # second biggest

            if biggestContour.size != 0 and gradePoints.size != 0:
                cv2.drawContours(imgBiggestContours, biggestContour, -1, (0, 255, 0), 20)
                cv2.drawContours(imgBiggestContours, gradePoints, -1, (0, 0, 255), 20)

                # rearranging the the corner points correctly of both rectangles 
                # (like finding out top left, top right, bottom left, bottom right corner points)
                # calling the function from the utils file
                biggestContour = reorder(biggestContour)
                gradePoints = reorder(gradePoints)

                # After getting the points extracting the both rectangles (OMR, Grade) from the image.
                point1 = np.float32(biggestContour)
                point2 = np.float32([[0, 0], [widthImg, 0], [0, heightImg], [widthImg, heightImg]])
                matrix = cv2.getPerspectiveTransform(point1, point2)
                imgWarpColored = cv2.warpPerspective(img, matrix, (widthImg, heightImg))

                gradePoint1 = np.float32(gradePoints)
                gradePoint2 = np.float32([[0, 0], [325, 0], [0, 150], [325, 150]])
                gradeMatrix = cv2.getPerspectiveTransform(gradePoint1, gradePoint2)
                imgGradeWarpColored = cv2.warpPerspective(img, gradeMatrix, (325, 150))

                # After extracting the OMR rectangle converting that extracted image into binary image 
                # (only black and white pixels will be there. 0 and 255 only)

                # applying the binary threshold
                imgWarpGray = cv2.cvtColor(imgWarpColored, cv2.COLOR_BGR2GRAY)
                imgThresh = cv2.threshold(imgWarpGray, 170, 255, cv2.THRESH_BINARY_INV)[1]

                # Then we split the image into 5 for each row to get each bubbles.
                # caling the function from utils file
                boxes = splitBoxes(imgThresh, questions, choices)
                
                pixelVal = np.zeros((questions, choices))
                columnCount = 0
                rowCount = 0

                # for a row which bubble have the most number of 255s in it, that will be the answer marked in the image. 
                # like that we find every answers that marked in the image.

                # box with most non zero values will be the answer of that row
                # finding index values of the correct answers
                for box in boxes:
                    pixelVal[rowCount][columnCount] = cv2.countNonZero(box)
                    columnCount += 1
                    if columnCount == choices:
                        columnCount = 0
                        rowCount += 1

                myIndex = []
                for i in range(0, questions):
                    arr = pixelVal[i]
                    count_greater_than_5 = sum(1 for value in arr if value > 5000)
                    # Check if the count is greater than 1
                    if count_greater_than_5 > 1 or count_greater_than_5 < 1:
                        myIndex.append(-1)
                    else:
                        myIndexVal = np.where(arr==np.amax(arr))
                        myIndex.append(myIndexVal[0][0])
                
                # also calculating the grade by comparing it with the answers that we have predefined.
                # Grading
                grading = []
                for i in range(0, questions):
                    if answers[i] == myIndex[i]:
                        grading.append(1)
                    else:
                        grading.append(0)
                
                temp_grading = grading.copy()

                if negative_marking:
                    for i in range(len(myIndex)):
                        if myIndex[i] != -1 and temp_grading[i] == 0:
                            temp_grading[i] -= 1/3

                score = (sum(temp_grading)/questions) * 100
                score = round(score, 1)
                score = max(score, 0.0)
                if score == 100.0:
                    score = 100

                # now we have to mark the right and wrong in the OMR sheet that we extracted from the image.
                # for that also we use cv2 to draw green if the answer is correct, red if the answer marked is wrong. 
                # if its wrong marking the correct answer with a small green dot.
                # displaying the answers in the image
                imgResult = imgWarpColored.copy()
                # calling the function from utils file
                imgResult = showAnswers(imgResult, myIndex, grading, answers, questions, choices)

                # now we need to make these markings inside the original image. so taking the markings
                imgRawDrawing = np.zeros_like(imgWarpColored)
                imgRawDrawing = showAnswers(imgRawDrawing, myIndex, grading, answers, questions, choices)

                # after that we took the drawings(markings) only. we need to show that in the real image. 
                # the real image may not be in correct shape. it may be little tilted. 
                # so we make inverse that drawings to be correctly fit in the real image.
                invMatrix = cv2.getPerspectiveTransform(point2, point1)
                imgInvWrap = cv2.warpPerspective(imgRawDrawing, invMatrix, (widthImg, heightImg))

                # after inversing the drawings we add that to the real image and we can get the markings will be correctly aligned to each bubbles.
                # making the final image
                finalImg = cv2.addWeighted(finalImg, 0.8, imgInvWrap, 1, 0)

                # also we found out the grade before. and we add that grade into the small rectangle.
                # adding the Grade in the box
                imgRawGrade = np.zeros_like(imgGradeWarpColored)
                cv2.putText(imgRawGrade, str(score) + '%', (20, 100), cv2.FONT_HERSHEY_COMPLEX, 3, (0, 256, 256), 3)

                gradeInvMatrix = cv2.getPerspectiveTransform(gradePoint2, gradePoint1)
                imgInvGradeWarp = cv2.warpPerspective(imgRawGrade, gradeInvMatrix, (widthImg, heightImg))

                # The final Image
                finalImg = cv2.addWeighted(finalImg, 1, imgInvGradeWarp, 1, 0)

                return finalImg, score
            
        except:
            print('An Error Occured')

# function to find out the rectangle edges
def rectContour(contours):
    rectangleContour = []
    for i in contours:
        area = cv2.contourArea(i)
        if area > 50:
            perimeter = cv2.arcLength(i, True)
            # approximation of corner points of each rectangle
            approx = cv2.approxPolyDP(i, 0.02*perimeter, True)
            if len(approx) == 4:
                rectangleContour.append(i)

    rectangleContour = sorted(rectangleContour, key=cv2.contourArea, reverse=True)
    return rectangleContour

# finding the corner points of the rectangles
def getCornerPoints(contour):
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02*perimeter, True)
    return approx

# reordring the points because if we dont do it then the image will not get properly
def reorder(myPoints):
    myPoints = myPoints.reshape((4, 2))
    myPointsNew = np.zeros((4, 1, 2), np.int32)
    add = myPoints.sum(1)
    diff = np.diff(myPoints, axis=1)
    # adding the points so that we can under stand the points order.
    # the minimum numbered point will be the top right and the maximum will be the bottom right
    myPointsNew[0] = myPoints[np.argmin(add)] # top left
    myPointsNew[3] = myPoints[np.argmax(add)] # bottom right
    myPointsNew[1] = myPoints[np.argmin(diff)] # bottom left
    myPointsNew[2] = myPoints[np.argmax(diff)] # top right

    return myPointsNew

# function for splitting the box into five equal parts
def splitBoxes(img, questions, choices):
    rows = np.vsplit(img, questions)

    boxes = []
    for r in rows:
        cols = np.hsplit(r, choices)
        for box in cols:
            boxes.append(box)
    return boxes

# function for marking the bubbles in the OMR sheet
def showAnswers(img, myIndex, grading, answers, questions, choices):
    sectionWidth = int(img.shape[1]/questions)
    sectionHeight = int(img.shape[1]/choices)

    for i in range(0, questions):
        myAns = myIndex[i]

        cX = (myAns * sectionWidth) + sectionWidth // 2
        cY = (i * sectionHeight) + sectionHeight // 2

        if grading[i]:
            cv2.circle(img, (cX, cY), 50, (0, 255, 0), cv2.FILLED)
        elif grading[i] == 0 and myAns == -1: # checking wheather the bubble is marked nothing or more than one 
            lineX = (sectionWidth * questions)
            img = cv2.line(img, (50, cY), (lineX - 50, cY), (0, 0, 255), 70)

            cX = (answers[i] * sectionWidth) + sectionWidth // 2
            cv2.circle(img, (cX, cY), 20, (0, 255, 0), cv2.FILLED)
        else:
            cv2.circle(img, (cX, cY), 50, (0, 0, 255), cv2.FILLED)

            cX = (answers[i] * sectionWidth) + sectionWidth // 2
            cv2.circle(img, (cX, cY), 20, (0, 255, 0), cv2.FILLED)

    return img

# function for converting the answers a, b, c, d, e  into  0, 1, 2, 3, 4
def convertAnswers(answers):
    result = []

    for letter in answers:
        value = ord(letter.lower()) - ord('a')
        result.append(value)

    return result
