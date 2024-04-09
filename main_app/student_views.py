import json
import math
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *


def student_home(request):
    student = get_object_or_404(Student, admin=request.user)
    
    
    
    total_subject = Subject.objects.filter(course=student.course).count()
    subs=Subject.objects.filter(course=student.course)
    total_attendance = AttendanceReport.objects.filter(student=student).count()
    total_present = AttendanceReport.objects.filter(student=student, status=True).count()
    student = request.user.student

    # Retrieve all assignments submitted by the current student
    submitted_assignments = AssignmentSubmission.objects.filter(student=student)

    # Get the IDs of submitted assignments
    submitted_assignment_ids = [submission.assignment.id for submission in submitted_assignments]

    # Retrieve all assignments associated with subjects the student is enrolled in
    enrolled_subjects = student.course.subject_set.all()
    assignments_to_display = Assignment.objects.filter(subject__in=enrolled_subjects)

    # Filter out assignments that the student has already submitted
    assignments_to_display = assignments_to_display.exclude(id__in=submitted_assignment_ids)

    # Filter out assignments that are past their due date
    current_time = datetime.now()
    assignments_to_display = assignments_to_display.filter(due_date__gte=current_time)
    remaining_assignments_count = assignments_to_display.count()
    
    student = get_object_or_404(Student, admin=request.user)
    results = StudentResult.objects.filter(student=student).order_by('-created_at')
    latest_result = results.first() if results.exists() else None
    
    # Get the subject name associated with the latest result
    latest_subject_name = latest_result.subject.name if latest_result else None
    
    # Get the previous result if available
    previous_result = None
    if len(results) > 1:
        previous_result = results[1]
    previous_subject_name=previous_result.subject.name
    
    
    
    if total_attendance == 0:  # Don't divide. DivisionByZero
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present/total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    subject_name = []
    data_present = []
    data_absent = []
    subjects = Subject.objects.filter(course=student.course)
    for subject in subjects:
        attendance = Attendance.objects.filter(subject=subject)
        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, student=student).count()
        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, student=student).count()
        subject_name.append(subject.name)
        data_present.append(present_count)
        data_absent.append(absent_count)
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_subject': total_subject,
        'subjects': subjects,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': subject_name,
        'page_title': 'Student Homepage',
        'subs':subs,
        
        'remaining_assignments_count': remaining_assignments_count,
         'results': results,
        'latest_result': latest_result,
        'latest_subject_name': latest_subject_name,
        'previous_subject_name':previous_subject_name,
        'previous_result': previous_result,
       
        
        'results': results,
        
        


    }
    return render(request, 'student_template/home_content.html', context)


@ csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method != 'POST':
        course = get_object_or_404(Course, id=student.course.id)
        context = {
            'subjects': Subject.objects.filter(course=course),
            'page_title': 'View Attendance'
        }
        return render(request, 'student_template/student_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student=student)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_result(request):
    student = get_object_or_404(Student, admin=request.user)
    results = StudentResult.objects.filter(student=student).order_by('-created_at')
    latest_result = results.first() if results.exists() else None
    
    # Get the subject name associated with the latest result
    latest_subject_name = latest_result.subject.name if latest_result else None
    
    # Get the previous result if available
    previous_result = None
    if len(results) > 1:
        previous_result = results[1]
    previous_subject_name=previous_result.subject.name
    context = {
        'results': results,
        'latest_result': latest_result,
        'latest_subject_name': latest_subject_name,
        'previous_subject_name':previous_subject_name,
        'previous_result': previous_result,
        'page_title': "View Results"
    }
    return render(request, "student_template/student_view_result.html", context)

def student_view_assignment(request):
    # Assuming the logged-in user is a student
    student = request.user.student

    # Retrieve all assignments submitted by the current student
    submitted_assignments = AssignmentSubmission.objects.filter(student=student)

    # Get the IDs of submitted assignments
    submitted_assignment_ids = [submission.assignment.id for submission in submitted_assignments]

    # Retrieve all assignments associated with subjects the student is enrolled in
    enrolled_subjects = student.course.subject_set.all()
    assignments_to_display = Assignment.objects.filter(subject__in=enrolled_subjects)

    # Filter out assignments that the student has already submitted
    assignments_to_display = assignments_to_display.exclude(id__in=submitted_assignment_ids)

    # Filter out assignments that are past their due date
    current_time = datetime.now()
    assignments_to_display = assignments_to_display.filter(due_date__gte=current_time)
    remaining_assignments_count = assignments_to_display.count()
    
    context = {
        'remaining_assignments_count': remaining_assignments_count,
        'page_title': "Submit Assignments",
        'assignments': assignments_to_display
    }
    return render(request, "student_template/student_view_assignment.html", context)





















def student_submit_assignment(request, assignment_id):
    # Retrieve the assignment object based on the provided assignment_id
    assignment = get_object_or_404(Assignment, pk=assignment_id)

    if request.method == "POST":
        # If the request method is POST, process the form submission
        submission_file = request.FILES.get('submission_file')
        if submission_file:
            # If a file is provided, save the assignment submission
            submission = AssignmentSubmission.objects.create(
                assignment=assignment,
                student=request.user.student,
                submission_file=submission_file
            )
            messages.success(request, "Assignment submitted successfully.")
            return redirect('student_view_assignment')
        else:
            messages.error(request, "Please select a file to upload.")
            return redirect('student_view_assignment')

    context = {
        'page_title': "Submit Assignment",
        'assignment': assignment
    }
    return render(request, "student_template/student_submit_assignment.html", context)


